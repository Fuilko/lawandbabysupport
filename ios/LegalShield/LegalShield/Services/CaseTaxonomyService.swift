import Foundation

/// 案件分類スキーマの単一真実源（Single Source of Truth）
///
/// `data/case_taxonomy/taxonomy_v1.json` を読み込み、iOS 内部の `CaseCategory` enum と
/// 外部 agent (Python / Node) の両方が同じデータを参照できるようにする。
///
/// 同じ JSON ファイルを：
/// - iOS App (本クラス) が bundle resource として読込
/// - 外部 agent (Python: `import json; json.load(open('data/case_taxonomy/taxonomy_v1.json'))`) が直接読込
/// - FastAPI backend (`legalshield/backend/api.py`) が serve
@MainActor
public final class CaseTaxonomyService: ObservableObject {

    public static let shared = CaseTaxonomyService()

    @Published public private(set) var taxonomy: Taxonomy?
    @Published public private(set) var loadError: String?

    private init() {
        load()
    }

    public func load() {
        // 1. App bundle 内 (Resources)
        if let url = Bundle.main.url(forResource: "taxonomy_v1", withExtension: "json"),
           let data = try? Data(contentsOf: url) {
            decode(data)
            return
        }
        // 2. Documents/case_taxonomy/ (将来の OTA 更新用)
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
        if let docs = docs {
            let url = docs.appendingPathComponent("case_taxonomy/taxonomy_v1.json")
            if let data = try? Data(contentsOf: url) {
                decode(data)
                return
            }
        }
        loadError = "taxonomy_v1.json not found in bundle or Documents"
    }

    private func decode(_ data: Data) {
        do {
            self.taxonomy = try JSONDecoder().decode(Taxonomy.self, from: data)
            self.loadError = nil
        } catch {
            self.loadError = "decode failed: \(error)"
        }
    }

    // MARK: - クエリ

    public func category(byId id: String) -> CategoryEntry? {
        taxonomy?.categories.first(where: { $0.id == id })
    }

    public func categories(forPhase phase: Int) -> [CategoryEntry] {
        taxonomy?.categories.filter { $0.phase == phase } ?? []
    }

    public func defaultUrgency(for categoryId: String) -> String {
        category(byId: categoryId)?.defaultUrgency ?? "medium"
    }

    public func partners(for categoryId: String) -> [String] {
        category(byId: categoryId)?.defaultPartners ?? []
    }

    public func ragQuerySeeds(for categoryId: String) -> [String] {
        category(byId: categoryId)?.ragQuerySeeds ?? []
    }
}

// MARK: - JSON モデル

public struct Taxonomy: Codable {
    public let version: String
    public let generatedAt: String
    public let language: String
    public let purpose: String
    public let urgencyLevels: [UrgencyLevel]
    public let caseStatuses: [CaseStatusEntry]
    public let categories: [CategoryEntry]

    enum CodingKeys: String, CodingKey {
        case version
        case generatedAt = "generated_at"
        case language
        case purpose
        case urgencyLevels = "urgency_levels"
        case caseStatuses = "case_statuses"
        case categories
    }

    public struct UrgencyLevel: Codable {
        public let level: Int
        public let id: String
        public let labelJp: String
        public let labelZh: String
        public let color: String

        enum CodingKeys: String, CodingKey {
            case level, id, color
            case labelJp = "label_jp"
            case labelZh = "label_zh"
        }
    }

    public struct CaseStatusEntry: Codable {
        public let id: String
        public let labelJp: String
        public let labelZh: String
        enum CodingKeys: String, CodingKey {
            case id
            case labelJp = "label_jp"
            case labelZh = "label_zh"
        }
    }
}

public struct CategoryEntry: Codable, Identifiable {
    public let id: String
    public let phase: Int
    public let defaultUrgency: String
    public let labelJp: String
    public let labelZh: String
    public let iconSf: String?
    public let color: String?
    public let japaneseLegalDomains: [String]
    public let keyStatutes: [String]?
    public let defaultPartners: [String]?
    public let evidencePriority: [String]?
    public let ragQuerySeeds: [String]?
    public let caseStudies: [String]?

    enum CodingKeys: String, CodingKey {
        case id, phase, color
        case defaultUrgency = "default_urgency"
        case labelJp = "label_jp"
        case labelZh = "label_zh"
        case iconSf = "icon_sf"
        case japaneseLegalDomains = "japanese_legal_domains"
        case keyStatutes = "key_statutes"
        case defaultPartners = "default_partners"
        case evidencePriority = "evidence_priority"
        case ragQuerySeeds = "rag_query_seeds"
        case caseStudies = "case_studies"
    }
}
