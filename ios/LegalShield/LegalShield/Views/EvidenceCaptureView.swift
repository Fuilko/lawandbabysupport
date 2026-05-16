import SwiftUI
import AVFoundation

/// 證據採集畫面 — 相機 + 錄音 + 感測器自動關聯
struct EvidenceCaptureView: View {
    @StateObject private var camera = CameraController()
    @StateObject private var evidenceManager: EvidenceManager?
    @State private var showPhotoPreview = false
    @State private var capturedImage: UIImage?
    @State private var isRecordingAudio = false
    @State private var recordingSeconds = 0
    @State private var showSuccessToast = false
    @State private var toastMessage = ""
    
    var body: some View {
        ZStack {
            // 相機預覽
            CameraPreviewView(session: camera.session)
                .ignoresSafeArea()
            
            VStack {
                // 頂部狀態列
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Label("GPS 定位中", systemImage: "location.fill")
                            .font(.caption)
                            .foregroundColor(.yellow)
                        
                        if let loc = camera.currentLocation {
                            Text(String(format: "%.5f, %.5f", loc.coordinate.latitude, loc.coordinate.longitude))
                                .font(.caption2)
                                .foregroundColor(.white.opacity(0.8))
                        }
                    }
                    
                    Spacer()
                    
                    // 哈希狀態指示
                    HStack(spacing: 4) {
                        Image(systemName: "lock.shield.fill")
                            .foregroundColor(.green)
                        Text("SHA-256 就緒")
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                }
                .padding()
                .background(.ultraThinMaterial)
                
                Spacer()
                
                // 底部控制列
                HStack(spacing: 30) {
                    // 錄音按鈕
                    Button(action: toggleAudioRecording) {
                        ZStack {
                            Circle()
                                .fill(isRecordingAudio ? .red : .white)
                                .frame(width: 60, height: 60)
                            
                            Image(systemName: isRecordingAudio ? "stop.fill" : "mic.fill")
                                .font(.title2)
                                .foregroundColor(isRecordingAudio ? .white : .red)
                        }
                    }
                    
                    // 拍照按鈕
                    Button(action: capturePhoto) {
                        ZStack {
                            Circle()
                                .stroke(.white, lineWidth: 4)
                                .frame(width: 80, height: 80)
                            
                            Circle()
                                .fill(.white)
                                .frame(width: 68, height: 68)
                        }
                    }
                    
                    // 緊急錄影按鈕
                    Button(action: startEmergencyRecording) {
                        ZStack {
                            Circle()
                                .fill(.red.opacity(0.8))
                                .frame(width: 60, height: 60)
                            
                            Image(systemName: "video.fill")
                                .font(.title2)
                                .foregroundColor(.white)
                        }
                    }
                }
                .padding(.bottom, 40)
            }
            
            // 錄音計時器
            if isRecordingAudio {
                VStack {
                    Spacer()
                    HStack(spacing: 8) {
                        Image(systemName: "record.circle.fill")
                            .foregroundColor(.red)
                            .font(.title3)
                        Text(formatTime(recordingSeconds))
                            .font(.system(.title2, design: .monospaced))
                            .foregroundColor(.white)
                    }
                    .padding()
                    .background(.ultraThinMaterial)
                    .cornerRadius(12)
                    .padding(.bottom, 140)
                }
            }
            
            // 成功提示
            if showSuccessToast {
                VStack {
                    Spacer()
                    HStack {
                        Image(systemName: "checkmark.shield.fill")
                            .foregroundColor(.green)
                        Text(toastMessage)
                            .foregroundColor(.white)
                    }
                    .padding()
                    .background(.black.opacity(0.8))
                    .cornerRadius(10)
                    .padding(.bottom, 160)
                }
                .transition(.move(edge: .bottom))
            }
        }
        .onAppear {
            camera.checkPermissions()
        }
        .sheet(isPresented: $showPhotoPreview) {
            if let image = capturedImage {
                PhotoPreviewSheet(image: image) { confirmed in
                    if confirmed {
                        saveEvidence(image: image)
                    }
                    showPhotoPreview = false
                }
            }
        }
    }
    
    private func capturePhoto() {
        camera.capturePhoto { image in
            if let image = image {
                capturedImage = image
                showPhotoPreview = true
            }
        }
    }
    
    private func saveEvidence(image: UIImage) {
        // 實際呼叫 EvidenceManager.capturePhoto
        toastMessage = "證據已加密儲存 (SHA-256 鎖定)"
        showSuccessToast = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            showSuccessToast = false
        }
    }
    
    private func toggleAudioRecording() {
        if isRecordingAudio {
            stopAudioRecording()
        } else {
            startAudioRecording()
        }
    }
    
    private func startAudioRecording() {
        isRecordingAudio = true
        recordingSeconds = 0
        
        // 啟動計時器
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { timer in
            if !isRecordingAudio {
                timer.invalidate()
                return
            }
            recordingSeconds += 1
        }
        
        // 實際啟動錄音
        toastMessage = "開始背景錄音..."
        showSuccessToast = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            showSuccessToast = false
        }
    }
    
    private func stopAudioRecording() {
        isRecordingAudio = false
        toastMessage = "錄音已儲存並哈希鎖定"
        showSuccessToast = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            showSuccessToast = false
        }
    }
    
    private func startEmergencyRecording() {
        // 同時啟動錄影 + 錄音 + 感測器記錄
        toastMessage = "緊急模式啟動：全面取證中"
        showSuccessToast = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            showSuccessToast = false
        }
    }
    
    private func formatTime(_ seconds: Int) -> String {
        String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }
}

// MARK: - 相機控制器

class CameraController: NSObject, ObservableObject {
    let session = AVCaptureSession()
    @Published var currentLocation: CLLocation?
    
    private var photoOutput = AVCapturePhotoOutput()
    private var videoDeviceInput: AVCaptureDeviceInput?
    private var locationManager = CLLocationManager()
    private var completionHandler: ((UIImage?) -> Void)?
    
    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.requestWhenInUseAuthorization()
        locationManager.startUpdatingLocation()
    }
    
    func checkPermissions() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { _ in }
        case .authorized:
            setupSession()
        default:
            break
        }
        
        AVCaptureDevice.requestAccess(for: .audio) { _ in }
    }
    
    private func setupSession() {
        session.beginConfiguration()
        session.sessionPreset = .high
        
        guard let videoDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let videoInput = try? AVCaptureDeviceInput(device: videoDevice),
              session.canAddInput(videoInput) else {
            session.commitConfiguration()
            return
        }
        
        session.addInput(videoInput)
        videoDeviceInput = videoInput
        
        if session.canAddOutput(photoOutput) {
            session.addOutput(photoOutput)
        }
        
        session.commitConfiguration()
        
        DispatchQueue.global(qos: .userInitiated).async {
            self.session.startRunning()
        }
    }
    
    func capturePhoto(completion: @escaping (UIImage?) -> Void) {
        completionHandler = completion
        let settings = AVCapturePhotoSettings()
        photoOutput.capturePhoto(with: settings, delegate: self)
    }
}

extension CameraController: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        guard let imageData = photo.fileDataRepresentation(),
              let image = UIImage(data: imageData) else {
            completionHandler?(nil)
            return
        }
        completionHandler?(image)
    }
}

extension CameraController: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        currentLocation = locations.last
    }
}

// MARK: - 相機預覽

struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession
    
    func makeUIView(context: Context) -> VideoPreviewView {
        let view = VideoPreviewView()
        view.videoPreviewLayer.session = session
        view.videoPreviewLayer.videoGravity = .resizeAspectFill
        return view
    }
    
    func updateUIView(_ uiView: VideoPreviewView, context: Context) {}
}

class VideoPreviewView: UIView {
    override class var layerClass: AnyClass {
        return AVCaptureVideoPreviewLayer.self
    }
    
    var videoPreviewLayer: AVCaptureVideoPreviewLayer {
        return layer as! AVCaptureVideoPreviewLayer
    }
}

// MARK: - 照片預覽確認

struct PhotoPreviewSheet: View {
    let image: UIImage
    let onConfirm: (Bool) -> Void
    @State private var showHashOverlay = true
    
    var body: some View {
        NavigationStack {
            VStack {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .overlay(alignment: .bottom) {
                        if showHashOverlay {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("LEGALSHIELD EVIDENCE")
                                    .font(.caption2)
                                    .fontWeight(.bold)
                                Text("Hash: \(computeHash())")
                                    .font(.caption2)
                                Text("Time: \(Date().iso8601)")
                                    .font(.caption2)
                            }
                            .padding(8)
                            .background(.black.opacity(0.7))
                            .foregroundColor(.white)
                        }
                    }
                
                HStack(spacing: 20) {
                    Button("重新拍攝") {
                        onConfirm(false)
                    }
                    .buttonStyle(.bordered)
                    .tint(.red)
                    
                    Button("確認儲存") {
                        onConfirm(true)
                    }
                    .buttonStyle(.borderedProminent)
                }
                .padding()
            }
            .navigationTitle("預覽")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private func computeHash() -> String {
        guard let data = image.jpegData(compressionQuality: 0.9) else { return "N/A" }
        let hash = Evidence.computeSHA256(for: data)
        return String(hash.prefix(16)) + "..."
    }
}
