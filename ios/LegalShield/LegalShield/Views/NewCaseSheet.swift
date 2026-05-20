import SwiftUI

/// 建立新案件 Sheet
struct NewCaseSheet: View {
    @ObservedObject var viewModel: CaseViewModel
    @Environment(\.dismiss) private var dismiss
    
    @State private var title: String = ""
    @State private var selectedCategory: CaseCategory = .childAbuse
    @State private var victimAlias: String = ""
    @State private var victimAge: String = ""
    @State private var institution: String = ""
    @State private var description: String = ""
    @State private var urgency: UrgencyLevel = .high
    @State private var showQuickTemplates = true
    
    var body: some View {
        NavigationStack {
            Form {
                Section("クイックテンプレート") {
                    if showQuickTemplates {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 10) {
                                QuickTemplateButton(
                                    icon: "figure.child",
                                    title: "幼稚園虐待",
                                    color: .red
                                ) {
                                    applyTemplate(.childAbuse)
                                }
                                
                                QuickTemplateButton(
                                    icon: "eye.slash.fill",
                                    title: "盗撮調査",
                                    color: .purple
                                ) {
                                    applyTemplate(.hiddenCamera)
                                }
                                
                                QuickTemplateButton(
                                    icon: "house.fill",
                                    title: "家庭暴力",  // DV
                                    color: .orange
                                ) {
                                    applyTemplate(.domesticViolence)
                                }
                                
                                QuickTemplateButton(
                                    icon: "building.columns.fill",
                                    title: "イジメ・虐め",
                                    color: .blue
                                ) {
                                    applyTemplate(.schoolBullying)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                
                Section("基本情報") {
                    TextField("案件タイトル", text: $title)
                    
                    Picker("案件カテゴリー", selection: $selectedCategory) {
                        ForEach(CaseCategory.allCases, id: \.self) { category in
                            Text(category.displayName).tag(category)
                        }
                    }
                    
                    Picker("緊急度", selection: $urgency) {
                        ForEach(UrgencyLevel.allCases, id: \.self) { level in
                            Text(level.displayName).tag(level)
                        }
                    }
                }
                
                Section("当事者情報") {
                    TextField("被害者エイリアス (例: 太郎くん)", text: $victimAlias)
                    
                    HStack {
                        Text("年齢")
                        Spacer()
                        TextField("歳", text: $victimAge)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 80)
                    }
                    
                    TextField("機関名 (例: XX幼稚園)", text: $institution)
                }
                
                Section("事案の概要") {
                    TextEditor(text: $description)
                        .frame(minHeight: 100)
                }
                
                Section {
                    Button(action: createCase) {
                        HStack {
                            Spacer()
                            Text("案件を作成して証拠保全を開始")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                    .disabled(title.isEmpty)
                }
            }
            .navigationTitle("新規案件の作成")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("キャンセル") { dismiss() }
                }
            }
        }
    }
    
    private func applyTemplate(_ category: CaseCategory) {
        selectedCategory = category
        urgency = .critical
        
        switch category {
        case .childAbuse:
            title = "幼稚園での児童虐待案件"
            victimAlias = "太郎くん"
            institution = ""
            
        case .hiddenCamera:
            title = "盗撮・プライバシー侵害の調査"
            institution = ""
            
        case .domesticViolence:
            title = "家庭内暴力事件"
            victimAlias = "被害者"
            
        case .schoolBullying:
            title = "学校でのイジメ事件"
            institution = ""
            
        default:
            break
        }
        
        showQuickTemplates = false
    }
    
    private func createCase() {
        let age = Int(victimAge)
        
        let newCase = viewModel.createCase(
            title: title,
            category: selectedCategory,
            victimAlias: victimAlias.isEmpty ? "匿名" : victimAlias,  // 同一漢字
            victimAge: age,
            institution: institution.isEmpty ? nil : institution,
            description: description.isEmpty ? nil : description
        )
        
        // 設定緊急等級
        newCase.urgency = urgency.rawValue
        
        dismiss()
    }
}

// MARK: - 快速範本按鈕

struct QuickTemplateButton: View {
    let icon: String
    let title: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundColor(color)
                Text(title)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.primary)
            }
            .frame(width: 90, height: 80)
            .background(color.opacity(0.1))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(color.opacity(0.2), lineWidth: 1)
            )
            .cornerRadius(12)
        }
    }
}
