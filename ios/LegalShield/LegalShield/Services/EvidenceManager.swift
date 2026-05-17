import Foundation
import CryptoKit
import SwiftData
import CoreLocation
import UIKit

/// 證據管理器 — 司法級存證鏈核心
/// 
/// 責任：
/// 1. 採集證據（相機、錄音、感測器）
/// 2. 即時 SHA-256 哈希
/// 3. AES-256-GCM 加密儲存
/// 4. 證據鏈 (Merkle chain) 維護
/// 5. 匯出法院可用格式
class EvidenceManager: NSObject, ObservableObject {
    
    // MARK: - Published
    
    @Published var currentCase: LegalCase?
    @Published var lastEvidence: Evidence?
    @Published var isRecording: Bool = false
    @Published var recordingDuration: TimeInterval = 0
    
    // MARK: - 依賴
    
    private let modelContainer: ModelContainer
    private let modelContext: ModelContext
    private let locationManager = CLLocationManager()
    private var currentLocation: CLLocation?
    
    // 錄音相關
    private var audioRecorder: AVAudioRecorder?
    private var recordingTimer: Timer?
    private var recordingStartTime: Date?
    
    // 證據鏈索引
    private var chainIndex: Int = 0
    private var lastHash: String?
    
    // MARK: - 初始化
    
    init(container: ModelContainer) {
        self.modelContainer = container
        self.modelContext = ModelContext(container)
        super.init()
        
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
        locationManager.requestWhenInUseAuthorization()
    }
    
    // MARK: - 案件管理
    
    func createCase(
        title: String,
        category: CaseCategory,
        victimAlias: String = "匿名",
        victimAge: Int? = nil,
        institution: String? = nil
    ) -> LegalCase {
        let newCase = LegalCase(
            title: title,
            category: category,
            victimAlias: victimAlias,
            victimAge: victimAge,
            institutionName: institution
        )
        modelContext.insert(newCase)
        try? modelContext.save()
        
        currentCase = newCase
        chainIndex = 0
        lastHash = nil
        
        return newCase
    }
    
    func loadCase(id: UUID) -> LegalCase? {
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == id }
        )
        return try? modelContext.fetch(descriptor).first
    }
    
    // MARK: - 照片證據
    
    /// 拍照並立即存證
    func capturePhoto(image: UIImage, isFirstDisclosure: Bool = false) async throws -> Evidence {
        guard let caseId = currentCase?.id else {
            throw EvidenceError.noActiveCase
        }
        
        // 1. 取得圖片數據
        guard let imageData = image.jpegData(compressionQuality: 0.9) else {
            throw EvidenceError.imageEncodingFailed
        }
        
        // 2. 加入浮水印 (時間 + 位置 + 哈希預留)
        let watermarkedImage = addWatermark(to: image, caseId: caseId)
        guard let watermarkedData = watermarkedImage.jpegData(compressionQuality: 0.9) else {
            throw EvidenceError.imageEncodingFailed
        }
        
        // 3. 計算 SHA-256
        let hash = Evidence.computeSHA256(for: watermarkedData)
        
        // 4. 加密儲存
        let fileName = "evidence_\(Date().iso8601)_photo.jpg"
        let filePath = try await saveEncrypted(data: watermarkedData, fileName: fileName)
        
        // 5. 建立證據記錄
        let evidence = Evidence(
            caseId: caseId,
            type: .photo,
            fileName: fileName,
            filePath: filePath,
            fileSize: watermarkedData.count,
            sha256Hash: hash,
            previousHash: lastHash,
            chainIndex: chainIndex,
            latitude: currentLocation?.coordinate.latitude,
            longitude: currentLocation?.coordinate.longitude,
            locationAccuracy: currentLocation?.horizontalAccuracy,
            isFirstDisclosure: isFirstDisclosure
        )
        
        // 6. 更新鏈
        chainIndex += 1
        lastHash = hash
        
        // 7. 儲存到資料庫
        modelContext.insert(evidence)
        currentCase?.addEvidence(evidence)
        try modelContext.save()
        
        lastEvidence = evidence
        return evidence
    }
    
    // MARK: - 錄音證據
    
    /// 開始錄音（緊急模式）
    func startRecording(isFirstDisclosure: Bool = false) throws {
        guard currentCase != nil else {
            throw EvidenceError.noActiveCase
        }
        
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .default)
        try session.setActive(true)
        
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 2,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        let fileName = "evidence_\(Date().iso8601)_audio.m4a"
        let url = getDocumentsDirectory().appendingPathComponent(fileName)
        
        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.record()
        
        isRecording = true
        recordingStartTime = Date()
        recordingDuration = 0
        
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let start = self?.recordingStartTime else { return }
            self?.recordingDuration = Date().timeIntervalSince(start)
        }
    }
    
    /// 停止錄音並存證
    func stopRecording() async throws -> Evidence {
        guard let recorder = audioRecorder else {
            throw EvidenceError.noActiveRecording
        }
        
        recorder.stop()
        audioRecorder = nil
        isRecording = false
        recordingTimer?.invalidate()
        recordingTimer = nil
        
        let url = recorder.url
        let data = try Data(contentsOf: url)
        let hash = Evidence.computeSHA256(for: data)
        
        // 加密儲存
        let fileName = url.lastPathComponent
        let encryptedPath = try await saveEncrypted(data: data, fileName: fileName)
        
        guard let caseId = currentCase?.id else {
            throw EvidenceError.noActiveCase
        }
        
        let evidence = Evidence(
            caseId: caseId,
            type: .audio,
            fileName: fileName,
            filePath: encryptedPath,
            fileSize: data.count,
            sha256Hash: hash,
            previousHash: lastHash,
            chainIndex: chainIndex,
            latitude: currentLocation?.coordinate.latitude,
            longitude: currentLocation?.coordinate.longitude,
            locationAccuracy: currentLocation?.horizontalAccuracy,
            interviewDuration: recordingDuration
        )
        
        chainIndex += 1
        lastHash = hash
        
        modelContext.insert(evidence)
        currentCase?.addEvidence(evidence)
        try modelContext.save()
        
        lastEvidence = evidence
        return evidence
    }
    
    // MARK: - 感測器證據
    
    /// 將感測器異常數據存入證據庫
    func captureSensorEvidence(
        sensorData: SensorData,
        anomalyDescription: String
    ) throws -> Evidence {
        guard let caseId = currentCase?.id else {
            throw EvidenceError.noActiveCase
        }
        
        // 將感測器數據轉為 JSON
        let snapshot = SensorReadingSnapshot(
            timestamp: sensorData.timestamp,
            sensorType: sensorData.type.rawValue,
            value: sensorData.value,
            unit: sensorData.unit,
            deviceName: sensorData.deviceName
        )
        
        let jsonData = try JSONEncoder().encode([snapshot])
        let hash = Evidence.computeSHA256(for: jsonData)
        
        let fileName = "sensor_\(Date().iso8601)_\(sensorData.type.rawValue).json"
        let filePath = try await saveEncrypted(data: jsonData, fileName: fileName)
        
        let evidence = Evidence(
            caseId: caseId,
            type: .sensorData,
            fileName: fileName,
            filePath: filePath,
            fileSize: jsonData.count,
            sha256Hash: hash,
            previousHash: lastHash,
            chainIndex: chainIndex,
            latitude: currentLocation?.coordinate.latitude,
            longitude: currentLocation?.coordinate.longitude
        )
        
        // 加入感測器快照
        evidence.sensorReadings = [snapshot]
        evidence.notes = anomalyDescription
        
        chainIndex += 1
        lastHash = hash
        
        modelContext.insert(evidence)
        currentCase?.addEvidence(evidence)
        try modelContext.save()
        
        return evidence
    }
    
    // MARK: - 加密儲存
    
    /// AES-256-GCM 加密儲存
    /// internal 訪問權限，讓同模組的 importer/generator 可以使用
    func saveEncrypted(data: Data, fileName: String) async throws -> String {
        let symmetricKey = try await getOrCreateEncryptionKey()
        let nonce = AES.GCM.Nonce()
        let sealedBox = try AES.GCM.seal(data, using: symmetricKey, nonce: nonce)
        
        guard let combined = sealedBox.combined else {
            throw EvidenceError.encryptionFailed
        }
        
        let url = getDocumentsDirectory().appendingPathComponent(fileName + ".encrypted")
        try combined.write(to: url)
        
        return url.path
    }
    
    /// 取得或建立加密金鑰
    private func getOrCreateEncryptionKey() async throws -> SymmetricKey {
        let keyTag = "com.legalshield.encryption.key"
        let keyData: Data
        
        if let existingData = try? KeychainHelper.load(key: keyTag) {
            keyData = existingData
        } else {
            keyData = SymmetricKey(size: .bits256).withUnsafeBytes { Data($0) }
            try KeychainHelper.save(key: keyTag, data: keyData)
        }
        
        return SymmetricKey(data: keyData)
    }
    
    /// 解密檔案
    func decryptFile(at path: String) throws -> Data {
        let symmetricKey = try getOrCreateEncryptionKey().get()
        let encryptedData = try Data(contentsOf: URL(fileURLWithPath: path))
        let sealedBox = try AES.GCM.SealedBox(combined: encryptedData)
        return try AES.GCM.open(sealedBox, using: symmetricKey)
    }
    
    // MARK: - 浮水印
    
    private func addWatermark(to image: UIImage, caseId: UUID) -> UIImage {
        let renderer = UIGraphicsImageRenderer(size: image.size)
        return renderer.image { context in
            image.draw(at: .zero)
            
            let text = """
            LEGALSHIELD EVIDENCE
            Case: \(caseId.uuidString.prefix(8))
            Time: \(Date().iso8601)
            Location: \(formatLocation())
            """
            
            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.monospacedSystemFont(ofSize: 14, weight: .bold),
                .foregroundColor: UIColor.red.withAlphaComponent(0.8)
            ]
            
            let textSize = text.size(withAttributes: attributes)
            let rect = CGRect(
                x: 10,
                y: image.size.height - textSize.height - 10,
                width: textSize.width + 10,
                height: textSize.height + 10
            )
            
            UIColor.black.withAlphaComponent(0.5).setFill()
            context.fill(rect)
            text.draw(at: CGPoint(x: 15, y: image.size.height - textSize.height - 5), withAttributes: attributes)
        }
    }
    
    private func formatLocation() -> String {
        guard let loc = currentLocation else { return "N/A" }
        return String(format: "%.5f, %.5f", loc.coordinate.latitude, loc.coordinate.longitude)
    }
    
    // MARK: - 匯出
    
    /// 產生證據保全證明書 (JSON)
    func generateCertificate(for caseId: UUID) throws -> Data {
        guard let caseItem = loadCase(id: caseId),
              let evidenceItems = caseItem.evidenceItems else {
            throw EvidenceError.caseNotFound
        }
        
        let certificate: [String: Any] = [
            "case_id": caseId.uuidString,
            "case_title": caseItem.title,
            "generated_at": Date().iso8601,
            "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] ?? "unknown",
            "evidence_count": evidenceItems.count,
            "chain_verified": caseItem.chainOfCustodyComplete,
            "evidence": evidenceItems.map { e in
                [
                    "index": e.chainIndex,
                    "id": e.id.uuidString,
                    "type": e.type,
                    "sha256": e.sha256Hash,
                    "previous_hash": e.previousHash ?? "GENESIS",
                    "timestamp": e.createdAt.iso8601,
                    "file_size": e.fileSize
                ]
            },
            "verification_code": Evidence.computeSHA256(for: try JSONEncoder().encode(evidenceItems.map { $0.sha256Hash }))
        ]
        
        return try JSONSerialization.data(withJSONObject: certificate, options: .prettyPrinted)
    }
    
    // MARK: - 輔助方法
    
    private func getDocumentsDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("LegalShieldEvidence", isDirectory: true)
    }
}

// MARK: - 錯誤定義

enum EvidenceError: Error, LocalizedError {
    case noActiveCase
    case noActiveRecording
    case imageEncodingFailed
    case encryptionFailed
    case caseNotFound
    
    var errorDescription: String? {
        switch self {
        case .noActiveCase: return "沒有活躍的案件，請先建立案件"
        case .noActiveRecording: return "沒有進行中的錄音"
        case .imageEncodingFailed: return "圖片編碼失敗"
        case .encryptionFailed: return "加密失敗"
        case .caseNotFound: return "找不到案件"
        }
    }
}

// MARK: - Keychain Helper

enum KeychainHelper {
    static func save(key: String, data: Data) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw EvidenceError.encryptionFailed
        }
    }
    
    static func load(key: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        return result as? Data
    }
}

// MARK: - CLLocationManagerDelegate

extension EvidenceManager: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        currentLocation = locations.last
    }
    
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("[Location] Error: \(error.localizedDescription)")
    }
}
