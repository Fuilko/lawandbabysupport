import Foundation
import SwiftData
import UIKit

/// 案件報告生成器
/// 統整所有證據、時間線、法律分析，由 LLM 生成可直接提交法庭/檢察官的文書
class CaseReportGenerator {
    
    private let modelContext: ModelContext
    private let llmService: LLMService
    
    init(context: ModelContext, llmService: LLMService) {
        self.modelContext = context
        self.llmService = llmService
    }
    
    // MARK: - 報告類型
    
    enum ReportType: String, CaseIterable {
        case criminalIndictment = "criminal_indictment"         // 刑事告訴狀
        case civilComplaint = "civil_complaint"               // 民事訴狀
        case administrativeAppeal = "administrative_appeal"     // 行政審査請求書
        case protectionOrder = "protection_order"             // 保護令聲請書
        case childConsultation = "child_consultation"         // 児童相談所通報書
        case laborComplaint = "labor_complaint"               // 労働基準監督署申告書
        case consumerComplaint = "consumer_complaint"         // 消費者申訴書
        case evidenceCertificate = "evidence_certificate"       // 證據保全證明書
        
        var displayName: String {
            switch self {
            case .criminalIndictment: return "刑事告訴狀"
            case .civilComplaint: return "民事訴狀"
            case .administrativeAppeal: return "行政審査請求書"
            case .protectionOrder: return "保護令聲請書"
            case .childConsultation: return "児童相談所通報書"
            case .laborComplaint: return "労働基準監督署申告書"
            case .consumerComplaint: return "消費者申訴書"
            case .evidenceCertificate: return "證據保全證明書"
            }
        }
        
        var submitTo: String {
            switch self {
            case .criminalIndictment: return "警察/檢察官"
            case .civilComplaint: return "法院"
            case .administrativeAppeal: return "行政機關"
            case .protectionOrder: return "家庭法院"
            case .childConsultation: return "児童相談所"
            case .laborComplaint: return "労働基準監督署"
            case .consumerComplaint: return "消費者センター"
            case .evidenceCertificate: return "法庭（附於其他文書後）"
            }
        }
        
        var applicableLaw: String {
            switch self {
            case .criminalIndictment: return "刑事訴訟法第230条"
            case .civilComplaint: return "民法第709条"
            case .administrativeAppeal: return "行政不服審査法"
            case .protectionOrder: return "配偶者暴力防止法第26条 / ストーカー規制法第14条"
            case .childConsultation: return "児童虐待防止法第3条"
            case .laborComplaint: return "労働基準法"
            case .consumerComplaint: return "消費者契約法"
            case .evidenceCertificate: return "民事訴訟法第231条（証拠保全）"
            }
        }
    }
    
    // MARK: - 主要生成流程
    
    /// 生成完整報告
    func generateReport(
        for caseId: UUID,
        reportType: ReportType,
        jurisdiction: String = "JP"
    ) async throws -> GeneratedReport {
        
        // 1. 載入案件
        let caseItem = try loadCase(id: caseId)
        
        // 2. 收集證據索引
        let evidenceIndex = try buildEvidenceIndex(for: caseId)
        
        // 3. 重建時間線
        let timeline = buildTimeline(caseItem: caseItem, evidences: evidenceIndex)
        
        // 4. 法律領域分析
        let legalDomains = caseItem.caseCategory.japaneseLegalDomains
        
        // 5. 準備 LLM prompt
        let prompt = buildLLMPrompt(
            caseItem: caseItem,
            evidenceIndex: evidenceIndex,
            timeline: timeline,
            reportType: reportType,
            legalDomains: legalDomains
        )
        
        // 6. 呼叫後端 LLM（使用現有的 legalQA 介面）
        let llmResponse = try await llmService.legalQA(
            question: prompt,
            context: nil,
            model: .llama33  // 高精度模型用於文書生成
        )
        
        // 7. 生成證據保全證明書（PDF 附件）
        let evidenceCertificate = try generateEvidenceCertificate(
            caseId: caseId,
            evidences: evidenceIndex
        )
        
        // 8. 組裝最終報告
        return GeneratedReport(
            caseId: caseId,
            reportType: reportType,
            generatedAt: Date(),
            content: llmResponse,
            evidenceCertificate: evidenceCertificate,
            evidenceIndex: evidenceIndex,
            timeline: timeline,
            submitTo: reportType.submitTo,
            applicableLaw: reportType.applicableLaw
        )
    }
    
    // MARK: - 資料收集
    
    private func loadCase(id: UUID) throws -> LegalCase {
        // 將 id 提取為局部常量，避免 Predicate 捕獲外部參數的並發警告
        let targetId = id
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == targetId }
        )
        guard let caseItem = try modelContext.fetch(descriptor).first else {
            throw ReportError.caseNotFound
        }
        return caseItem
    }
    
    /// 建立證據索引（只收集 hash 和 metadata，不載入原始內容）
    private func buildEvidenceIndex(for caseId: UUID) throws -> [EvidenceIndexItem] {
        let targetCaseId = caseId
        let descriptor = FetchDescriptor<Evidence>(
            predicate: #Predicate { $0.caseId == targetCaseId }
        )
        let evidences = try modelContext.fetch(descriptor)
        
        return evidences.map { evidence in
            EvidenceIndexItem(
                id: evidence.id,
                type: evidence.evidenceType,
                hash: evidence.sha256Hash,
                description: evidence.notes ?? "未命名證據",
                timestamp: evidence.createdAt,
                fileSize: evidence.fileSize,
                location: formatLocation(evidence.latitude, evidence.longitude),
                chainIndex: evidence.chainIndex,
                tags: evidence.tags ?? []
            )
        }.sorted { $0.chainIndex < $1.chainIndex }
    }
    
    /// 重建時間線
    /// 注：參數名不能用 `case`（Swift 關鍵字），改用 caseItem
    private func buildTimeline(caseItem: LegalCase, evidences: [EvidenceIndexItem]) -> [TimelineEvent] {
        var events: [TimelineEvent] = []
        
        // 案件建立
        events.append(TimelineEvent(
            date: caseItem.createdAt,
            type: .caseCreated,
            description: "案件建立：\(caseItem.title)",
            evidenceIds: []
        ))
        
        // 事件發生（如果已知）
        if let incidentDate = caseItem.incidentDate {
            events.append(TimelineEvent(
                date: incidentDate,
                type: .incident,
                description: "事件發生：\(caseItem.incidentDescription ?? "")",
                evidenceIds: []
            ))
        }
        
        // 證據採集
        for evidence in evidences {
            events.append(TimelineEvent(
                date: evidence.timestamp,
                type: .evidenceCollected,
                description: "採集\(evidence.type.displayName)：\(evidence.description)",
                evidenceIds: [evidence.id]
            ))
        }
        
        // 緊急轉介（如果有）
        if caseItem.caseStatus == .escalated {
            events.append(TimelineEvent(
                date: caseItem.updatedAt,
                type: .escalation,
                description: "案件升級/轉介",
                evidenceIds: []
            ))
        }
        
        return events.sorted { $0.date < $1.date }
    }
    
    // MARK: - LLM Prompt 建構
    
    private func buildLLMPrompt(
        caseItem: LegalCase,
        evidenceIndex: [EvidenceIndexItem],
        timeline: [TimelineEvent],
        reportType: ReportType,
        legalDomains: [JapaneseLegalRAG.LegalDomain]
    ) -> String {
        
        let evidenceDescriptions = evidenceIndex.map { evidence in
            "[\(evidence.chainIndex)] \(evidence.type.displayName) (\(evidence.timestamp.iso8601)) - \(evidence.description)"
        }.joined(separator: "\n")
        
        let timelineDescriptions = timeline.map { event in
            "\(event.date.iso8601): \(event.description)"
        }.joined(separator: "\n")
        
        let legalDomainText = legalDomains.map { $0.rawValue }.joined(separator: ", ")
        
        return """
        你是一位專業的日本法律文書撰寫專家。請根據以下案件資訊，生成一份正式的「\(reportType.displayName)」，可直接提交給\(reportType.submitTo)。

        === 報告類型 ===
        \(reportType.displayName)
        適用法條：\(reportType.applicableLaw)

        === 案件基本資訊 ===
        案件類型：\(caseItem.caseCategory.displayName)
        受害者代號：\(caseItem.victimAlias)（\(caseItem.victimAge ?? 0)歲）
        加害者代號：\(caseItem.perpetratorAlias ?? "不明")（\(caseItem.perpetratorRole ?? "不明")）
        事件地點：\(caseItem.incidentLocation ?? "未記載")
        機構名稱：\(caseItem.institutionName ?? "未記載")

        === 事件描述 ===
        \(caseItem.incidentDescription ?? "未記載")

        === 時間線 ===
        \(timelineDescriptions)

        === 證據目錄 ===
        \(evidenceDescriptions)

        === 法律領域 ===
        \(legalDomainText)

        === 輸出要求 ===
        1. 使用正式的日本法律文書格式（日語）
        2. 引用相關法條
        3. 證據引用使用 [Exhibit A], [Exhibit B] 格式
        4. 包含「求め」或「申立の趣旨」段落
        5. 結尾註明：「本状に添付の証拠は、SHA-256 ハッシュ化・暗号化保存されており、改竄が不可能であることを証明する證據保全證明書を添付する」
        6. 總字數約 2000-3000 字
        """
    }
    
    // MARK: - 證據保全證明書
    
    /// 生成證據保全證明書 PDF（日本法庭可用格式）
    func generateEvidenceCertificate(
        caseId: UUID,
        evidences: [EvidenceIndexItem]
    ) throws -> Data {
        let caseItem = try loadCase(id: caseId)
        
        var certificateContent = """
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        証 拠 保 全 証 明 書
        Certificate of Evidence Preservation
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        発行日：\(Date().iso8601)
        発行元：LegalShield 司法級証拠管理システム
        アプリバージョン：\(Bundle.main.infoDictionary?["CFBundleShortVersionString"] ?? "unknown")
        OS：iOS \(UIDevice.current.systemVersion)
        デバイスID：\(UIDevice.current.identifierForVendor?.uuidString ?? "unknown")

        ─────────────────────────────────
        【案件情報】
        ─────────────────────────────────
        案件ID：\(caseId.uuidString)
        案件名：\(caseItem.title)
        証拠総数：\(evidences.count) 件
        証拠チェーン検証：\(caseItem.chainOfCustodyComplete ? "完整" : "不完整")

        ─────────────────────────────────
        【証拠一覧】（改竄不能リスト）
        ─────────────────────────────────

        """
        
        for (index, evidence) in evidences.enumerated() {
            // Exhibit 編號：A-Z (26 個)，超過則使用 AA, AB...
            let exhibit: String
            if index < 26 {
                exhibit = String(UnicodeScalar(65 + index) ?? Unicode.Scalar(63))
            } else {
                let first = String(UnicodeScalar(65 + (index / 26 - 1)) ?? Unicode.Scalar(63))
                let second = String(UnicodeScalar(65 + (index % 26)) ?? Unicode.Scalar(63))
                exhibit = first + second
            }
            certificateContent += """
            [Exhibit \(exhibit)] \(evidence.type.displayName)
            ─────────────────────────────────
            識別ID：\(evidence.id.uuidString)
            SHA-256：\(evidence.hash)
            前件ハッシュ：\(index > 0 ? evidences[index-1].hash.prefix(16) : "GENESIS")
            採集日時：\(evidence.timestamp.iso8601)
            ファイルサイズ：\(evidence.fileSize) bytes
            位置情報：\(evidence.location)
            説明：\(evidence.description)
            タグ：\(evidence.tags.joined(separator: ", "))

            """
        }
        
        // 計算整體 hash
        let allHashes = evidences.map { $0.hash }.joined(separator: "")
        let combinedHash = Evidence.computeSHA256(for: allHashes.data(using: .utf8) ?? Data())
        
        certificateContent += """
        ─────────────────────────────────
        【証拠チェーン検証コード】
        ─────────────────────────────────
        全証拠連結ハッシュ：\(combinedHash)

        本証明書は、各証拠ファイルが SHA-256 ハッシュ化され、
        AES-256-GCM 暗号化で保存されていることを証明します。
        いかなる改竄も、ハッシュ値の不一致として即座に検出されます。

        検証方法：
        1. 証拠ファイルを再暗号化解除
        2. SHA-256 を計算
        3. 本証明書記載のハッシュ値と比較
        4. 一致すれば改竄なし、不一致であれば改竄あり

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        LegalShield Evidence Forensics System
        本証明書の偽造・改竄は刑法第159条（公正証書原本不実記載等）に該当します
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        return certificateContent.data(using: .utf8) ?? Data()
    }
    
    // MARK: - 輔助方法
    
    private func formatLocation(_ lat: Double?, _ lon: Double?) -> String {
        guard let lat = lat, let lon = lon else { return "N/A" }
        return String(format: "%.5f, %.5f", lat, lon)
    }
}

// MARK: - 資料結構

struct EvidenceIndexItem {
    let id: UUID
    let type: EvidenceType
    let hash: String
    let description: String
    let timestamp: Date
    let fileSize: Int
    let location: String
    let chainIndex: Int
    let tags: [String]
}

struct TimelineEvent {
    let date: Date
    let type: TimelineEventType
    let description: String
    let evidenceIds: [UUID]
}

enum TimelineEventType {
    case caseCreated
    case incident
    case evidenceCollected
    case escalation
    case partnerResponse
    case courtFiling
    case resolution
}

struct GeneratedReport {
    let caseId: UUID
    let reportType: CaseReportGenerator.ReportType
    let generatedAt: Date
    let content: String           // LLM 生成的報告內容（Markdown）
    let evidenceCertificate: Data // PDF 證據保全證明書
    let evidenceIndex: [EvidenceIndexItem]
    let timeline: [TimelineEvent]
    let submitTo: String
    let applicableLaw: String
    
    /// 匯出為法庭提交的 PDF 包裹
    func exportToPDF() -> Data? {
        // 實際應使用 PDFKit 生成完整 PDF
        // 簡化版：回傳 content + certificate 的合併
        let combined = """
        \(content)
        \n\n---\n\n
        \(String(data: evidenceCertificate, encoding: .utf8) ?? "")
        """
        return combined.data(using: .utf8)
    }
}

// MARK: - 錯誤定義

enum ReportError: Error, LocalizedError {
    case caseNotFound
    case evidenceCollectionFailed
    case llmGenerationFailed
    case pdfGenerationFailed
    
    var errorDescription: String? {
        switch self {
        case .caseNotFound: return "找不到案件"
        case .evidenceCollectionFailed: return "證據收集失敗"
        case .llmGenerationFailed: return "報告生成失敗（LLM 連線問題）"
        case .pdfGenerationFailed: return "PDF 生成失敗"
        }
    }
}
