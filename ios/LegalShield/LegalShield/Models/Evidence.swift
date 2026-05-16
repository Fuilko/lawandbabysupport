import Foundation
import CryptoKit
import SwiftData
import CoreLocation

/// 證據類型
enum EvidenceType: String, Codable, CaseIterable {
    case photo = "photo"
    case video = "video"
    case audio = "audio"
    case document = "document"
    case sensorData = "sensor_data"
    case screenshot = "screenshot"
    case transcript = "transcript"
    case medicalRecord = "medical_record"
    
    var icon: String {
        switch self {
        case .photo: return "camera.fill"
        case .video: return "video.fill"
        case .audio: return "waveform"
        case .document: return "doc.text.fill"
        case .sensorData: return "sensor.tag.fill"
        case .screenshot: return "rectangle.on.rectangle"
        case .transcript: return "text.bubble.fill"
        case .medicalRecord: return "heart.text.square.fill"
        }
    }
    
    var displayName: String {
        switch self {
        case .photo: return "照片"
        case .video: return "影片"
        case .audio: return "錄音"
        case .document: return "文件"
        case .sensorData: return "感測器數據"
        case .screenshot: return "截圖"
        case .transcript: return "逐字稿"
        case .medicalRecord: return "醫療記錄"
        }
    }
}

/// 證據狀態
enum EvidenceStatus: String, Codable {
    case collected = "collected"       // 已採集
    case hashed = "hashed"             // 已哈希鎖定
    case encrypted = "encrypted"       // 已加密
    case verified = "verified"         // 已驗證鏈完整性
    case exported = "exported"         // 已匯出
}

/// 單一證據項目 — 司法級存證
@Model
final class Evidence {
    @Attribute(.unique) var id: UUID
    var caseId: UUID                  // 所屬案件
    var type: String                  // EvidenceType.rawValue
    var createdAt: Date
    var fileName: String
    var filePath: String?             // 本地加密儲存路徑
    var fileSize: Int
    
    // 核心：不可竄改的證據鏈
    var sha256Hash: String            // 原始檔案 SHA-256
    var previousHash: String?       // 證據鏈上一筆的 hash (Merkle chain)
    var chainIndex: Int               // 在證據鏈中的順序
    
    // 時空戳記
    var latitude: Double?             // GPS (可選)
    var longitude: Double?
    var locationAccuracy: Double?
    var timezone: String
    
    // 裝置資訊 (防止偽造)
    var deviceID: String              // 裝置 UUID
    var appVersion: String
    var osVersion: String
    
    // 感測器關聯
    var sensorReadings: [SensorReadingSnapshot]?
    
    // 訪談相關 (如果是童言童語錄音)
    var isFirstDisclosure: Bool       // 是否為「初次陳述」
    var interviewDuration: TimeInterval?
    var leadingQuestionCount: Int     // 系統偵測到的誘導問句數
    var transcript: String?           // 語音轉文字結果
    
    // 狀態與備註
    var status: String                // EvidenceStatus.rawValue
    var notes: String?
    var tags: [String]?
    
    // MARK: - Init
    
    init(
        id: UUID = UUID(),
        caseId: UUID,
        type: EvidenceType,
        fileName: String,
        filePath: String? = nil,
        fileSize: Int,
        sha256Hash: String,
        previousHash: String? = nil,
        chainIndex: Int,
        latitude: Double? = nil,
        longitude: Double? = nil,
        locationAccuracy: Double? = nil,
        timezone: String = TimeZone.current.identifier,
        deviceID: String = UIDevice.current.identifierForVendor?.uuidString ?? "unknown",
        appVersion: String = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0",
        osVersion: String = UIDevice.current.systemVersion,
        isFirstDisclosure: Bool = false,
        status: EvidenceStatus = .collected
    ) {
        self.id = id
        self.caseId = caseId
        self.type = type.rawValue
        self.createdAt = Date()
        self.fileName = fileName
        self.filePath = filePath
        self.fileSize = fileSize
        self.sha256Hash = sha256Hash
        self.previousHash = previousHash
        self.chainIndex = chainIndex
        self.latitude = latitude
        self.longitude = longitude
        self.locationAccuracy = locationAccuracy
        self.timezone = timezone
        self.deviceID = deviceID
        self.appVersion = appVersion
        self.osVersion = osVersion
        self.isFirstDisclosure = isFirstDisclosure
        self.leadingQuestionCount = 0
        self.status = status.rawValue
    }
    
    // MARK: - 計算屬性
    
    var evidenceType: EvidenceType {
        EvidenceType(rawValue: type) ?? .document
    }
    
    var evidenceStatus: EvidenceStatus {
        EvidenceStatus(rawValue: status) ?? .collected
    }
    
    var chainOfCustody: String {
        """
        Chain of Custody
        =================
        Index: \(chainIndex)
        Evidence ID: \(id.uuidString)
        SHA-256: \(sha256Hash)
        Previous: \(previousHash ?? "GENESIS")
        Device: \(deviceID)
        Timestamp: \(createdAt.iso8601)
        Location: \(formatLocation())
        Status: \(status)
        """
    }
    
    private func formatLocation() -> String {
        guard let lat = latitude, let lon = longitude else { return "N/A" }
        return String(format: "%.6f, %.6f", lat, lon)
    }
    
    // MARK: - 靜態方法
    
    /// 計算檔案的 SHA-256
    static func computeSHA256(for data: Data) -> String {
        let hash = SHA256.hash(data: data)
        return hash.compactMap { String(format: "%02x", $0) }.joined()
    }
    
    /// 計算檔案的 SHA-256 (從 URL)
    static func computeSHA256(for url: URL) -> String? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return computeSHA256(for: data)
    }
    
    /// 驗證檔案完整性
    func verifyIntegrity(for data: Data) -> Bool {
        let currentHash = Evidence.computeSHA256(for: data)
        return currentHash == sha256Hash
    }
}

// MARK: - Sensor Reading Snapshot

/// 證據採集時的感測器讀數快照
struct SensorReadingSnapshot: Codable {
    let timestamp: Date
    let sensorType: String        // "heart_rate", "accelerometer", etc.
    let value: Double
    let unit: String
    let deviceName: String?
    
    var display: String {
        "\(sensorType): \(String(format: "%.1f", value)) \(unit)"
    }
}

// MARK: - Date Extension

extension Date {
    var iso8601: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: self)
    }
}
