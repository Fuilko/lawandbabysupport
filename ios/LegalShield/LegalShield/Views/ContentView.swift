import SwiftUI
import SwiftData

/// App 主畫面 — 緊急啟動中心
struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = CaseViewModel()
    @State private var selectedTab = 0
    @State private var showEmergencyModal = false
    
    var body: some View {
        TabView(selection: $selectedTab) {
            // Tab 1: 案件總覽
            CaseListView(viewModel: viewModel)
                .tabItem {
                    Label("案件", systemImage: "folder.fill")
                }
                .tag(0)
            
            // Tab 2: 感測器儀表板
            SensorDashboardView()
                .tabItem {
                    Label("感測器", systemImage: "sensor.tag.fill")
                }
                .tag(1)
            
            // Tab 3: 證據中心
            EvidenceCenterView(viewModel: viewModel)
                .tabItem {
                    Label("證據", systemImage: "lock.shield.fill")
                }
                .tag(2)
            
            // Tab 4: AI 分析
            AIAnalysisView(viewModel: viewModel)
                .tabItem {
                    Label("AI分析", systemImage: "brain.fill")
                }
                .tag(3)
            
            // Tab 5: 設定
            SettingsView()
                .tabItem {
                    Label("設定", systemImage: "gear")
                }
                .tag(4)
        }
        .overlay(alignment: .bottom) {
            // 緊急按鈕懸浮
            EmergencyButton(showModal: $showEmergencyModal)
                .padding(.bottom, 60)
        }
        .sheet(isPresented: $showEmergencyModal) {
            EmergencyActionSheet(viewModel: viewModel)
        }
    }
}

// MARK: - 案件列表

struct CaseListView: View {
    @ObservedObject var viewModel: CaseViewModel
    @Query(sort: \LegalCase.createdAt, order: .reverse) private var cases: [LegalCase]
    @State private var showNewCaseSheet = false
    
    var body: some View {
        NavigationStack {
            List {
                ForEach(cases) { caseItem in
                    CaseRowView(caseItem: caseItem)
                        .swipeActions(edge: .trailing) {
                            Button(role: .destructive) {
                                // 封存而非刪除
                            } label: {
                                Label("封存", systemImage: "archivebox")
                            }
                        }
                }
            }
            .listStyle(.plain)
            .navigationTitle("我的案件")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { showNewCaseSheet = true }) {
                        Image(systemName: "plus.circle.fill")
                            .font(.title2)
                    }
                }
            }
            .sheet(isPresented: $showNewCaseSheet) {
                NewCaseSheet(viewModel: viewModel)
            }
        }
    }
}

struct CaseRowView: View {
    let caseItem: LegalCase
    
    var body: some View {
        NavigationLink(value: caseItem) {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(caseItem.title)
                        .font(.headline)
                    Spacer()
                    UrgencyBadge(level: caseItem.urgencyLevel)
                }
                
                HStack(spacing: 8) {
                    Label(caseItem.caseCategory.displayName, systemImage: "doc.text")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    
                    Label("\(caseItem.evidenceCount) 項證據", systemImage: "lock.shield")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                
                HStack {
                    Text(caseItem.victimAlias)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                    
                    if let institution = caseItem.institutionName {
                        Text("• \(institution)")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                    
                    Spacer()
                    
                    Text("\(caseItem.daysSinceCreation) 天前")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            .padding(.vertical, 4)
        }
    }
}

struct UrgencyBadge: View {
    let level: UrgencyLevel
    
    var body: some View {
        Text(level.displayName)
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 8)
            .padding(.vertical, 2)
            .background(backgroundColor)
            .foregroundColor(.white)
            .clipShape(Capsule())
    }
    
    private var backgroundColor: Color {
        switch level {
        case .low: return .gray
        case .medium: return .yellow
        case .high: return .orange
        case .critical: return .red
        }
    }
}

// MARK: - 緊急按鈕

struct EmergencyButton: View {
    @Binding var showModal: Bool
    @State private var isPressed = false
    
    var body: some View {
        Button(action: { showModal = true }) {
            ZStack {
                Circle()
                    .fill(Color.red)
                    .frame(width: 64, height: 64)
                    .shadow(color: .red.opacity(0.4), radius: 8, x: 0, y: 4)
                
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.title2)
                    .foregroundColor(.white)
            }
        }
        .scaleEffect(isPressed ? 0.9 : 1.0)
        .animation(.spring(response: 0.3), value: isPressed)
    }
}

// MARK: - 緊急行動選單

struct EmergencyActionSheet: View {
    @ObservedObject var viewModel: CaseViewModel
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("緊急行動")
                    .font(.title)
                    .fontWeight(.bold)
                
                Text("選擇適當的緊急應對措施")
                    .foregroundStyle(.secondary)
                
                Spacer()
                
                VStack(spacing: 12) {
                    EmergencyActionButton(
                        icon: "phone.fill",
                        title: "撥打 110",
                        subtitle: "直接報警",
                        color: .red,
                        action: { /* 撥打 110 */ }
                    )
                    
                    EmergencyActionButton(
                        icon: "mic.fill",
                        title: "立即錄音取證",
                        subtitle: "背景錄音 + 時間戳鎖定",
                        color: .orange,
                        action: { /* 啟動錄音 */ }
                    )
                    
                    EmergencyActionButton(
                        icon: "camera.fill",
                        title: "拍照存證",
                        subtitle: "即時哈希 + GPS 定位",
                        color: .blue,
                        action: { /* 啟動相機 */ }
                    )
                    
                    EmergencyActionButton(
                        icon: "shield.fill",
                        title: "啟動防誘導訪談",
                        subtitle: "保護童言童語證據力",
                        color: .green,
                        action: { /* 啟動 InterviewCopilot */ }
                    )
                }
                
                Spacer()
            }
            .padding()
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("取消") { dismiss() }
                }
            }
        }
    }
}

struct EmergencyActionButton: View {
    let icon: String
    let title: String
    let subtitle: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 16) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundColor(color)
                    .frame(width: 40, height: 40)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.headline)
                        .foregroundColor(.primary)
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .foregroundColor(.secondary)
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
    }
}

// MARK: - 證據中心

struct EvidenceCenterView: View {
    @ObservedObject var viewModel: CaseViewModel
    
    var body: some View {
        NavigationStack {
            List {
                Section("快速取證") {
                    NavigationLink(destination: EvidenceCaptureView()) {
                        Label("拍照/錄影", systemImage: "camera.fill")
                    }
                    NavigationLink(destination: InterviewAssistView()) {
                        Label("防誘導訪談", systemImage: "mic.fill")
                    }
                    NavigationLink(destination: AntiSurveillanceView()) {
                        Label("反偷拍掃描", systemImage: "eye.slash.fill")
                    }
                }
                
                Section("證據庫") {
                    if let currentCase = viewModel.currentCase {
                        Text("案件：\(currentCase.title)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        
                        // 這裡顯示該案件的證據列表
                    } else {
                        Text("請先選擇或建立案件")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("證據中心")
        }
    }
}

// MARK: - AI 分析

struct AIAnalysisView: View {
    @ObservedObject var viewModel: CaseViewModel
    @State private var analysisResult: String = ""
    @State private var isAnalyzing = false
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    if let currentCase = viewModel.currentCase {
                        CaseSummaryCard(caseItem: currentCase)
                        
                        Button(action: { runAnalysis() }) {
                            HStack {
                                Image(systemName: "brain.fill")
                                Text(isAnalyzing ? "分析中..." : "執行 AI 分析")
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(12)
                        }
                        .disabled(isAnalyzing)
                        
                        if !analysisResult.isEmpty {
                            AnalysisResultCard(result: analysisResult)
                        }
                    } else {
                        EmptyStateView(
                            icon: "brain",
                            title: "選擇案件進行 AI 分析",
                            subtitle: "AI 將評估證據鏈完整性並提供策略建議"
                        )
                    }
                }
                .padding()
            }
            .navigationTitle("AI 分析")
        }
    }
    
    private func runAnalysis() {
        isAnalyzing = true
        // 實際呼叫 LLMService
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            analysisResult = "✅ 證據鏈完整性：B 級\n🎯 勝訴機率估計：65%\n\n建議補強方向：\n• 補充醫療診斷證明\n• 尋找目擊證人\n• 申請監視器調閱"
            isAnalyzing = false
        }
    }
}

struct CaseSummaryCard: View {
    let caseItem: LegalCase
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(caseItem.title)
                .font(.headline)
            Text(caseItem.caseCategory.displayName)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            HStack {
                Label("\(caseItem.evidenceCount) 項證據", systemImage: "doc.fill")
                Spacer()
                UrgencyBadge(level: caseItem.urgencyLevel)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

struct AnalysisResultCard: View {
    let result: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("分析結果")
                .font(.headline)
            Text(result)
                .font(.body)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - 設定

struct SettingsView: View {
    @AppStorage("apiEndpoint") private var apiEndpoint = "http://100.76.218.124:8000"
    @AppStorage("useMockData") private var useMockData = false
    
    var body: some View {
        NavigationStack {
            Form {
                Section("伺服器設定") {
                    TextField("API 端點", text: $apiEndpoint)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    
                    Toggle("使用模擬數據 (Simulator)", isOn: $useMockData)
                }
                
                Section("關於") {
                    HStack {
                        Text("版本")
                        Spacer()
                        Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                            .foregroundStyle(.secondary)
                    }
                    
                    Text("LegalShield — 被害者を支援し、誰も1人にはしない。")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("設定")
        }
    }
}

// MARK: - 空狀態

struct EmptyStateView: View {
    let icon: String
    let title: String
    let subtitle: String
    
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.headline)
            Text(subtitle)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 60)
    }
}
