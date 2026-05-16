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
                Section("快速範本") {
                    if showQuickTemplates {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 10) {
                                QuickTemplateButton(
                                    icon: "figure.child",
                                    title: "幼兒園虐待",
                                    color: .red
                                ) {
                                    applyTemplate(.childAbuse)
                                }
                                
                                QuickTemplateButton(
                                    icon: "eye.slash.fill",
                                    title: "偷拍調查",
                                    color: .purple
                                ) {
                                    applyTemplate(.hiddenCamera)
                                }
                                
                                QuickTemplateButton(
                                    icon: "house.fill",
                                    title: "家庭暴力",
                                    color: .orange
                                ) {
                                    applyTemplate(.domesticViolence)
                                }
                                
                                QuickTemplateButton(
                                    icon: "building.columns.fill",
                                    title: "校園霸凌",
                                    color: .blue
                                ) {
                                    applyTemplate(.schoolBullying)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                
                Section("基本資訊") {
                    TextField("案件標題", text: $title)
                    
                    Picker("案件類型", selection: $selectedCategory) {
                        ForEach(CaseCategory.allCases, id: \.self) { category in
                            Text(category.displayName).tag(category)
                        }
                    }
                    
                    Picker("緊急等級", selection: $urgency) {
                        ForEach(UrgencyLevel.allCases, id: \.self) { level in
                            Text(level.displayName).tag(level)
                        }
                    }
                }
                
                Section("當事人資訊") {
                    TextField("受害者代號 (如：小華)", text: $victimAlias)
                    
                    HStack {
                        Text("年齡")
                        Spacer()
                        TextField("歲", text: $victimAge)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 80)
                    }
                    
                    TextField("機構名稱 (如：XX幼兒園)", text: $institution)
                }
                
                Section("事件描述") {
                    TextEditor(text: $description)
                        .frame(minHeight: 100)
                }
                
                Section {
                    Button(action: createCase) {
                        HStack {
                            Spacer()
                            Text("建立案件並啟動證據保全")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                    .disabled(title.isEmpty)
                }
            }
            .navigationTitle("建立新案件")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("取消") { dismiss() }
                }
            }
        }
    }
    
    private func applyTemplate(_ category: CaseCategory) {
        selectedCategory = category
        urgency = .critical
        
        switch category {
        case .childAbuse:
            title = "幼兒園兒少保護案件"
            victimAlias = "小華"
            institution = ""
            
        case .hiddenCamera:
            title = "偷拍/隱私侵害調查"
            institution = ""
            
        case .domesticViolence:
            title = "家庭暴力事件"
            victimAlias = "受害者"
            
        case .schoolBullying:
            title = "校園霸凌事件"
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
            victimAlias: victimAlias.isEmpty ? "匿名" : victimAlias,
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
