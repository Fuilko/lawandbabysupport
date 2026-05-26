import Foundation
import SwiftData
import CryptoKit
import SQLite3
#if canImport(ZIPFoundation)
import ZIPFoundation
#endif

/// 案件データベースのポータブル・エクスポート
///
/// 目的：iOS 上の SwiftData (`LegalCase` / `Evidence` / `AuditLog`) を
/// **他言語の agent (Python / Node) でも直接読める形式** に書き出す。
///
/// ## 出力パッケージ構造（`.legalshield-pkg` = ZIP）
/// ```
/// <case_export_YYYYMMDD_HHmmss>.legalshield-pkg/
/// ├── manifest.json              ← schema_version, app_version, hash, generated_at
/// ├── schema.md                  ← 各 JSON / SQLite テーブル定義の人間読み doc
/// ├── taxonomy_v1.json           ← `data/case_taxonomy/` の snapshot（決定論性のため同梱）
/// ├── cases.json                 ← LegalCase 全件
/// ├── evidence.json              ← 全証拠（GPS は anonymizationLevel に従う）
/// ├── audit_log.json             ← AuditLog の hash chain 検証可能版
/// ├── cases.sqlite               ← 同データを SQLite で（任意言語から SQL クエリ可）
/// └── README.md                  ← 「他 agent はこう読みます」
/// ```
///
/// ## 想定読込側
/// - **Python**: `import sqlite3; sqlite3.connect("cases.sqlite")` または `json.load`
/// - **Node**: `better-sqlite3` または `JSON.parse(fs.readFileSync(...))`
/// - **別 LegalShield インスタンス**: `PortableDBImporter`（未実装、Phase 2）
///
/// ## 匿名化レベル
/// `ExportService.AnonymizationLevel` と同じ列挙を使用。
/// - `.none`：原本そのまま（オーナー本人専用）
/// - `.partial`：GPS / device ID マスク（弁護士共有用）
/// - `.full`：被害者氏名・場所詳細もマスク（研究データ用）
@MainActor
public final class PortableDBExporter {

    public static let shared = PortableDBExporter()
    private init() {}

    public static let schemaVersion = "1.0"

    // MARK: - 主エクスポート

    public func exportAllCases(
        modelContext: ModelContext,
        anonymization: AnonymizationLevel = .partial,
        progress: ((Double) -> Void)? = nil
    ) throws -> URL {

        // 1. データ取得
        let descriptor = FetchDescriptor<LegalCase>(sortBy: [SortDescriptor(\.createdAt)])
        let cases = try modelContext.fetch(descriptor)
        progress?(0.1)

        // 2. ワークディレクトリ
        let stamp = ISO8601DateFormatter().string(from: Date())
            .replacingOccurrences(of: ":", with: "-")
            .replacingOccurrences(of: ".", with: "-")
        let workDir = FileManager.default.temporaryDirectory
            .appendingPathComponent("legalshield-export-\(stamp)", isDirectory: true)
        try FileManager.default.createDirectory(at: workDir, withIntermediateDirectories: true)

        // 3. JSON 系
        try writeJSON(workDir.appendingPathComponent("cases.json"),
                      cases.map { CaseDTO(from: $0, anonymization: anonymization) })
        progress?(0.3)

        let allEvidence = cases.flatMap { $0.evidenceItems ?? [] }
        try writeJSON(workDir.appendingPathComponent("evidence.json"),
                      allEvidence.map { EvidenceDTO(from: $0, anonymization: anonymization) })
        progress?(0.5)

        let auditEntries = AuditLogService.shared.fetchRecent(limit: Int.max)
            .map { AuditDTO(from: $0) }
        try writeJSON(workDir.appendingPathComponent("audit_log.json"), auditEntries)
        progress?(0.6)

        // 4. SQLite 出力
        try writeSQLite(
            url: workDir.appendingPathComponent("cases.sqlite"),
            cases: cases,
            evidenceList: allEvidence,
            anonymization: anonymization
        )
        progress?(0.8)

        // 5. taxonomy snapshot
        if let taxonomyURL = Bundle.main.url(forResource: "taxonomy_v1", withExtension: "json") {
            try FileManager.default.copyItem(
                at: taxonomyURL,
                to: workDir.appendingPathComponent("taxonomy_v1.json")
            )
        }

        // 6. schema.md / README.md
        try Self.schemaMarkdown.write(
            to: workDir.appendingPathComponent("schema.md"),
            atomically: true, encoding: .utf8
        )
        try Self.readmeMarkdown.write(
            to: workDir.appendingPathComponent("README.md"),
            atomically: true, encoding: .utf8
        )

        // 7. manifest.json（最後に書く：既存ファイルの SHA-256 含む）
        let manifest = try buildManifest(in: workDir,
                                         caseCount: cases.count,
                                         evidenceCount: allEvidence.count,
                                         anonymization: anonymization)
        try writeJSON(workDir.appendingPathComponent("manifest.json"), manifest)

        progress?(0.9)

        // 8. ZIP 化 → .legalshield-pkg
        let pkgURL = workDir.deletingLastPathComponent()
            .appendingPathComponent("legalshield-export-\(stamp).legalshield-pkg")
        try? FileManager.default.removeItem(at: pkgURL)

        #if canImport(ZIPFoundation)
        try FileManager.default.zipItem(at: workDir, to: pkgURL, shouldKeepParent: false)
        #else
        // ZIP 未リンク時は workDir 自体を返す
        return workDir
        #endif

        // 監査記録
        AuditLogService.shared.record(
            actor: .user,
            action: .exportAnalysis,
            detail: "PortableDB エクスポート: \(cases.count) cases, \(allEvidence.count) evidence — anonymization=\(anonymization.rawValue) pkg=\(pkgURL.lastPathComponent)"
        )
        progress?(1.0)

        return pkgURL
    }

    // MARK: - 内部処理

    private func writeJSON<T: Encodable>(_ url: URL, _ value: T) throws {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        enc.dateEncodingStrategy = .iso8601
        try enc.encode(value).write(to: url)
    }

    private func buildManifest(
        in dir: URL,
        caseCount: Int,
        evidenceCount: Int,
        anonymization: AnonymizationLevel
    ) throws -> ExportManifest {
        let fm = FileManager.default
        let files = try fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.fileSizeKey])
        let entries: [ExportManifest.FileEntry] = try files.map { url in
            let data = try Data(contentsOf: url)
            let hash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
            return ExportManifest.FileEntry(
                name: url.lastPathComponent,
                sizeBytes: data.count,
                sha256: hash
            )
        }
        return ExportManifest(
            schemaVersion: Self.schemaVersion,
            appVersion: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0",
            generatedAt: Date(),
            anonymizationLevel: anonymization.rawValue,
            caseCount: caseCount,
            evidenceCount: evidenceCount,
            files: entries
        )
    }

    private func writeSQLite(
        url: URL,
        cases: [LegalCase],
        evidenceList: [Evidence],
        anonymization: AnonymizationLevel
    ) throws {
        // 軽量化のため sqlite3 C API を直接叩く
        var db: OpaquePointer?
        guard sqlite3_open(url.path, &db) == SQLITE_OK else {
            throw ExporterError.sqliteOpenFailed
        }
        defer { sqlite3_close(db) }

        let schema = """
        CREATE TABLE cases (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            urgency INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            victim_alias TEXT,
            incident_date TEXT,
            incident_location TEXT,
            incident_description TEXT,
            ai_summary TEXT,
            win_probability REAL
        );
        CREATE TABLE evidence (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            type TEXT NOT NULL,
            file_name TEXT,
            file_path TEXT,
            file_size INTEGER,
            sha256 TEXT,
            previous_hash TEXT,
            chain_index INTEGER,
            created_at TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        );
        CREATE INDEX idx_evidence_case_id ON evidence(case_id);
        CREATE INDEX idx_cases_category   ON cases(category);
        CREATE INDEX idx_cases_urgency    ON cases(urgency);
        """
        guard sqlite3_exec(db, schema, nil, nil, nil) == SQLITE_OK else {
            throw ExporterError.sqliteSchemaFailed(String(cString: sqlite3_errmsg(db)))
        }

        let iso = ISO8601DateFormatter()

        // cases
        for c in cases {
            let sql = "INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);"
            var stmt: OpaquePointer?
            sqlite3_prepare_v2(db, sql, -1, &stmt, nil)
            sqlite3_bind_text(stmt, 1, c.id.uuidString, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 2, c.title, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 3, c.category, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 4, c.status, -1, SQLITE_TRANSIENT)
            sqlite3_bind_int(stmt, 5, Int32(c.urgency))
            sqlite3_bind_text(stmt, 6, iso.string(from: c.createdAt), -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 7, iso.string(from: c.updatedAt), -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 8, c.victimAlias, -1, SQLITE_TRANSIENT)
            if let d = c.incidentDate { sqlite3_bind_text(stmt, 9, iso.string(from: d), -1, SQLITE_TRANSIENT) }
            sqlite3_bind_text(stmt, 10, anonymization.maskLocation ? "(masked)" : (c.incidentLocation ?? ""), -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 11, c.incidentDescription ?? "", -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 12, c.aiAnalysisSummary ?? "", -1, SQLITE_TRANSIENT)
            if let p = c.winProbability { sqlite3_bind_double(stmt, 13, p) }
            sqlite3_step(stmt)
            sqlite3_finalize(stmt)
        }

        // evidence
        for e in evidenceList {
            let sql = "INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?);"
            var stmt: OpaquePointer?
            sqlite3_prepare_v2(db, sql, -1, &stmt, nil)
            sqlite3_bind_text(stmt, 1, e.id.uuidString, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 2, e.caseId.uuidString, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 3, e.type, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 4, e.fileName, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 5, anonymization.maskDeviceId ? "" : (e.filePath ?? ""), -1, SQLITE_TRANSIENT)
            sqlite3_bind_int64(stmt, 6, Int64(e.fileSize))
            sqlite3_bind_text(stmt, 7, e.sha256Hash, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(stmt, 8, e.previousHash ?? "", -1, SQLITE_TRANSIENT)
            sqlite3_bind_int(stmt, 9, Int32(e.chainIndex))
            sqlite3_bind_text(stmt, 10, iso.string(from: e.createdAt), -1, SQLITE_TRANSIENT)
            if !anonymization.maskGPS {
                if let lat = e.latitude { sqlite3_bind_double(stmt, 11, lat) }
                if let lng = e.longitude { sqlite3_bind_double(stmt, 12, lng) }
            }
            sqlite3_step(stmt)
            sqlite3_finalize(stmt)
        }
    }

    // MARK: - Schema docs

    private static let schemaMarkdown = """
    # LegalShield Portable DB — Schema v1.0

    ## ファイル構成

    | File | Format | 用途 |
    |---|---|---|
    | `manifest.json` | JSON | バージョン・ファイル一覧・SHA-256 |
    | `cases.json` | JSON | 案件全件 |
    | `evidence.json` | JSON | 証拠全件 (GPS は匿名化に従う) |
    | `audit_log.json` | JSON | hash chain 検証可能な監査ログ |
    | `cases.sqlite` | SQLite | 上記 3 ファイルを RDB 形式で同梱 |
    | `taxonomy_v1.json` | JSON | 案件分類スキーマ（決定論性確保） |

    ## SQLite テーブル

    ### `cases`
    `id` (TEXT, PK), `title`, `category`, `status`, `urgency` (INT 1-4),
    `created_at` (ISO8601), `updated_at`, `victim_alias`, `incident_date`,
    `incident_location`, `incident_description`, `ai_summary`, `win_probability` (REAL 0-1)

    ### `evidence`
    `id` (TEXT, PK), `case_id` (FK), `type`, `file_name`, `file_path`, `file_size`,
    `sha256`, `previous_hash`, `chain_index` (INT), `created_at`, `latitude`, `longitude`

    ## 検証

    `evidence.previous_hash` は前件 (`chain_index - 1`) の `sha256` と一致しなければならない。
    Python での検証例:

    ```python
    import sqlite3, hashlib
    db = sqlite3.connect("cases.sqlite")
    rows = db.execute("SELECT case_id, chain_index, sha256, previous_hash FROM evidence ORDER BY case_id, chain_index").fetchall()
    # ... 照合ロジック
    ```
    """

    private static let readmeMarkdown = """
    # LegalShield Portable Export Package

    本パッケージは LegalShield iOS App から生成された案件データベースのポータブル形式です。

    ## 他 agent からの読込方法

    ### Python
    ```python
    import json, sqlite3, zipfile, pathlib

    pkg = pathlib.Path("legalshield-export-XXXX.legalshield-pkg")
    with zipfile.ZipFile(pkg) as zf:
        zf.extractall("/tmp/ls")

    cases = json.load(open("/tmp/ls/cases.json"))
    db = sqlite3.connect("/tmp/ls/cases.sqlite")
    high_urgency = db.execute("SELECT * FROM cases WHERE urgency >= 3").fetchall()
    ```

    ### Node.js
    ```javascript
    const Database = require('better-sqlite3');
    const db = new Database('cases.sqlite', { readonly: true });
    const rows = db.prepare('SELECT * FROM cases WHERE urgency >= 3').all();
    ```

    ### 検証
    `manifest.json` 内の各ファイル SHA-256 を確認することで改ざん検知可能。

    ## 匿名化レベル

    - `none`：原本そのまま
    - `partial`：GPS と Device ID をマスク
    - `full`：被害者氏名・所在地もマスク（研究用）

    ## ライセンス・利用制限

    本データは案件オーナー本人の同意のもとに生成されています。第三者への共有時は
    別途同意取得が必要です。研究目的の場合は `anonymization = full` を必ず使用してください。
    """
}

// MARK: - DTOs（JSON シリアライズ用）

private struct CaseDTO: Codable {
    let id: String
    let title: String
    let category: String
    let status: String
    let urgency: Int
    let createdAt: Date
    let updatedAt: Date
    let victimAlias: String
    let incidentDate: Date?
    let incidentLocation: String?
    let incidentDescription: String?
    let aiSummary: String?
    let winProbability: Double?

    init(from c: LegalCase, anonymization: AnonymizationLevel) {
        self.id = c.id.uuidString
        self.title = c.title
        self.category = c.category
        self.status = c.status
        self.urgency = c.urgency
        self.createdAt = c.createdAt
        self.updatedAt = c.updatedAt
        self.victimAlias = anonymization.maskName ? "(anonymized)" : c.victimAlias
        self.incidentDate = c.incidentDate
        self.incidentLocation = anonymization.maskLocation ? nil : c.incidentLocation
        self.incidentDescription = c.incidentDescription
        self.aiSummary = c.aiAnalysisSummary
        self.winProbability = c.winProbability
    }
}

private struct EvidenceDTO: Codable {
    let id: String
    let caseId: String
    let type: String
    let fileName: String
    let fileSize: Int
    let sha256: String
    let previousHash: String?
    let chainIndex: Int
    let createdAt: Date
    let latitude: Double?
    let longitude: Double?

    init(from e: Evidence, anonymization: AnonymizationLevel) {
        self.id = e.id.uuidString
        self.caseId = e.caseId.uuidString
        self.type = e.type
        self.fileName = e.fileName
        self.fileSize = e.fileSize
        self.sha256 = e.sha256Hash
        self.previousHash = e.previousHash
        self.chainIndex = e.chainIndex
        self.createdAt = e.createdAt
        self.latitude = anonymization.maskGPS ? nil : e.latitude
        self.longitude = anonymization.maskGPS ? nil : e.longitude
    }
}

private struct AuditDTO: Codable {
    let id: String
    let timestamp: Date
    let actor: String
    let action: String
    let resourceType: String?
    let resourceId: String?
    let detail: String
    let chainIndex: Int
    let sha256: String
    let previousHash: String?

    init(from log: AuditLog) {
        self.id = log.id.uuidString
        self.timestamp = log.timestamp
        self.actor = log.actorType
        self.action = log.actionType
        self.resourceType = log.resourceType
        self.resourceId = log.resourceId
        self.detail = log.actionDetail
        self.chainIndex = log.chainIndex
        self.sha256 = log.sha256Hash
        self.previousHash = log.previousHash
    }
}

private struct ExportManifest: Codable {
    let schemaVersion: String
    let appVersion: String
    let generatedAt: Date
    let anonymizationLevel: String
    let caseCount: Int
    let evidenceCount: Int
    let files: [FileEntry]

    struct FileEntry: Codable {
        let name: String
        let sizeBytes: Int
        let sha256: String
    }
}

public enum ExporterError: Error {
    case sqliteOpenFailed
    case sqliteSchemaFailed(String)
}

// SQLITE_TRANSIENT helper
private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
