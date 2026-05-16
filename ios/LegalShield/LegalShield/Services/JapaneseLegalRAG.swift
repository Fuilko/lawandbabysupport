import Foundation

/// 日本法規 RAG (Retrieval Augmented Generation) 知識庫
///
/// 責任：
/// 1. 管理日本核心法規的向量索引
/// 2. 根據案件類型，檢索最相關的法條與判例
/// 3. 為 LLMService 提供 context-augmented prompt
///
/// 法規清單 (Phase 1-4):
/// Phase 1: 児童虐待防止法、ストーカー規制法、刑法 (傷害、暴行、侮辱)
/// Phase 2: 労働基準法、労働契約法、消費者基本法、特定商取引法
/// Phase 3: 高齢者虐待防止法、介護保険法、行政手続法、行政事件訴訟法
/// Phase 4: 航空法、環境基本法、土壌汚染対策法
class JapaneseLegalRAG {
    
    // MARK: - 配置
    
    /// 法規向量資料庫端點 (LanceDB on Windows server)
    var vectorDBEndpoint: String = "http://100.76.218.124:8000/rag"
    
    /// 預設檢索結果數量
    var topK: Int = 5
    
    // MARK: - 法規領域定義
    
    enum LegalDomain: String, CaseIterable {
        // Phase 1: 兒少 + 偷拍
        case childAbuse = "児童虐待防止法"
        case stalking = "ストーカー規制法"
        case criminal = "刑法 (傷害・侮辱)"
        
        // Phase 2: 勞動 + 消費者
        case labor = "労働基準法"
        case laborContract = "労働契約法"
        case consumer = "消費者基本法"
        case specificCommercial = "特定商取引法"
        
        // Phase 3: 高齡 + 行政
        case elderAbuse = "高齢者虐待防止法"
        case longTermCare = "介護保険法"
        case administrative = "行政手続法"
        case adminLitigation = "行政事件訴訟法"
        
        // Phase 4: 無人機 + 環境
        case aviation = "航空法"
        case environmental = "環境基本法"
        case soilPollution = "土壌汚染対策法"
        
        var phase: Int {
            switch self {
            case .childAbuse, .stalking, .criminal: return 1
            case .labor, .laborContract, .consumer, .specificCommercial: return 2
            case .elderAbuse, .longTermCare, .administrative, .adminLitigation: return 3
            case .aviation, .environmental, .soilPollution: return 4
            }
        }
        
        var keyStatutes: [String] {
            switch self {
            case .childAbuse:
                return ["第2条 (児童虐待の定義)", "第3条 (通報義務)", "第10条 (児童相談所の介入)", "第33条 (一時保護)"]
            case .stalking:
                return ["第2条 (ストーカー行為の定義)", "第13条 (禁止命令)", "第18条 (罰則)"]
            case .criminal:
                return ["第204条 (傷害)", "第208条 (暴行)", "第222条 (侮辱)"]
            case .labor:
                return ["第32条 (休憩時間)", "第36条 (時間外労働)", "第66条 (災害補償)", "第100条 (罰則)"]
            case .laborContract:
                return ["第3条 (労働条件の明示)", "第8条 (賃金の支払義務)"]
            case .consumer:
                return ["第1条2項 (消費者の定義)", "第4条 (事業者の責務)"]
            case .specificCommercial:
                return ["第6条 (クーリング・オフ)", "第12条 (景品類の提供の制限)"]
            case .elderAbuse:
                return ["第2条 (高齢者虐待の定義)", "第5条 (通報義務)", "第20条 (措置命令)"]
            case .longTermCare:
                return ["第8条 (要介護認定)", "第25条 (居宅介護支援)"]
            case .administrative:
                return ["第13条 (聴聞)", "第24条 (審査請求)", "第38条 (訴訟提起)"]
            case .adminLitigation:
                return ["第9条 (原告適格)", "第23条 (審理の範囲)"]
            case .aviation:
                return ["第132条 (無人航空機の飛行)", "第149条 (許可・承認)"]
            case .environmental:
                return ["第2条 (基本理念)", "第16条 (環境影響評価)"]
            case .soilPollution:
                return ["第3条 (指定区域)", "第7条 (汚染状況調査義務)"]
            }
        }
    }
    
    // MARK: - 檢索
    
    /// 根據案件類型檢索相關法條
    func retrieveStatutes(for category: CaseCategory) async throws -> [RetrievedStatute] {
        let domains = mapCategoryToDomains(category)
        
        var allResults: [RetrievedStatute] = []
        for domain in domains {
            let results = try await queryVectorDB(domain: domain, query: category.displayName)
            allResults.append(contentsOf: results)
        }
        
        // 按相關度排序，取 topK
        return allResults.sorted { $0.relevanceScore > $1.relevanceScore }.prefix(topK).map { $0 }
    }
    
    /// 根據具體問題檢索判例
    func retrievePrecedents(question: String, domain: LegalDomain) async throws -> [RetrievedPrecedent] {
        return try await queryPrecedentDB(query: question, domain: domain.rawValue)
    }
    
    /// 生成 RAG-augmented prompt
    func generateAugmentedPrompt(
        userQuestion: String,
        caseCategory: CaseCategory,
        context: String? = nil
    ) async throws -> String {
        let statutes = try await retrieveStatutes(for: caseCategory)
        
        var prompt = """
        【日本法規依據】
        以下為與本案最相關的法條與解釋：
        
        """
        
        for (index, statute) in statutes.enumerated() {
            prompt += "\(index + 1). \(statute.title)\n"
            prompt += "   內容：\(statute.content.prefix(200))...\n"
            prompt += "   相關度：\(String(format: "%.2f", statute.relevanceScore))\n\n"
        }
        
        if let ctx = context {
            prompt += "【案情背景】\n\(ctx)\n\n"
        }
        
        prompt += "【使用者問題】\n\(userQuestion)\n\n"
        prompt += "請基於以上法規依據回答。若法規未明確規定，請說明「法規空白」與實務傾向。"
        
        return prompt
    }
    
    // MARK: - 私有方法
    
    private func mapCategoryToDomains(_ category: CaseCategory) -> [LegalDomain] {
        switch category {
        case .childAbuse, .schoolBullying:
            return [.childAbuse, .criminal]
        case .hiddenCamera, .stalking:
            return [.stalking, .criminal]
        case .domesticViolence:
            return [.criminal, .childAbuse]
        case .laborExploitation, .workplaceHarassment:
            return [.labor, .laborContract]
        case .consumerFraud, .contractTrap:
            return [.consumer, .specificCommercial]
        case .elderAbuse, .institutionalNeglect:
            return [.elderAbuse, .longTermCare]
        case .administrativeComplaint:
            return [.administrative, .adminLitigation]
        case .environmentalCrime:
            return [.environmental, .soilPollution]
        case .droneViolation, .privacyByDrone:
            return [.aviation, .criminal]
        case .general, .other:
            return [.criminal, .consumer]
        }
    }
    
    private func queryVectorDB(domain: LegalDomain, query: String) async throws -> [RetrievedStatute] {
        let requestBody: [String: Any] = [
            "domain": domain.rawValue,
            "query": query,
            "top_k": topK,
            "language": "ja"
        ]
        
        var request = URLRequest(url: URL(string: "\(vectorDBEndpoint)/search")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw RAGError.queryFailed
        }
        
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let results = json["results"] as? [[String: Any]] else {
            throw RAGError.parseError
        }
        
        return results.compactMap { dict in
            guard let title = dict["title"] as? String,
                  let content = dict["content"] as? String,
                  let score = dict["score"] as? Double else { return nil }
            return RetrievedStatute(title: title, content: content, relevanceScore: score)
        }
    }
    
    private func queryPrecedentDB(query: String, domain: String) async throws -> [RetrievedPrecedent] {
        // 簡化實作：回傳 mock 或呼叫 Windows API
        let requestBody: [String: Any] = [
            "query": query,
            "domain": domain,
            "top_k": 3,
            "source": "saikansho" // 最高裁判所判例
        ]
        
        var request = URLRequest(url: URL(string: "\(vectorDBEndpoint)/precedents")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        
        // 若伺服器未就緒，回傳空陣列
        return []
    }
}

// MARK: - 資料結構

struct RetrievedStatute: Codable {
    let title: String
    let content: String
    let relevanceScore: Double
}

struct RetrievedPrecedent: Codable {
    let caseNumber: String
    let court: String
    let date: String
    let summary: String
    let holding: String
    let relevanceScore: Double
}

// MARK: - 錯誤

enum RAGError: Error {
    case queryFailed
    case parseError
    case vectorDBNotAvailable
}
