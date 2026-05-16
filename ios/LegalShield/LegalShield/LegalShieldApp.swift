import SwiftUI
import SwiftData

/// LegalShield iOS App 入口
///
/// 架構：
/// - SwiftUI + SwiftData (iOS 17+)
/// - Protocol-Oriented Sensor Layer
/// - Combine 數據流
/// - CryptoKit 硬體級加密
@main
struct LegalShieldApp: App {
    
    // 共享的 ModelContainer
    let container: ModelContainer
    
    init() {
        // 設定 Model Schema
        let schema = Schema([
            LegalCase.self,
            Evidence.self
        ])
        
        let modelConfiguration = ModelConfiguration(
            schema: schema,
            isStoredInMemoryOnly: false  // 生產環境設為 false
        )
        
        do {
            container = try ModelContainer(
                for: schema,
                configurations: [modelConfiguration]
            )
        } catch {
            fatalError("Could not initialize ModelContainer: \(error)")
        }
        
        // App 啟動設定
        configureAppearance()
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .modelContainer(container)
                .environment(\.colorScheme, .dark)  // 預設深色模式 (隱私考量)
        }
    }
    
    private func configureAppearance() {
        // 深色模式為主 (減少公共場合使用時的視覺暴露)
        UITraitCollection.current = UITraitCollection(
            traitsFrom: [UITraitCollection.current, UITraitCollection(userInterfaceStyle: .dark)]
        )
    }
}

// MARK: - Preview

#Preview {
    let schema = Schema([LegalCase.self, Evidence.self])
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try! ModelContainer(for: schema, configurations: [config])
    
    ContentView()
        .modelContainer(container)
}
