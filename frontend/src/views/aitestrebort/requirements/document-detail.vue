<template>
  <div class="document-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack" type="text" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div class="title-section">
          <h1 class="page-title">{{ document?.title || '文档详情' }}</h1>
          <div class="document-meta">
            <el-tag :type="getStatusType(document?.status)">
              {{ getStatusText(document?.status) }}
            </el-tag>
            <span class="meta-item">{{ document?.word_count || 0 }} 字</span>
            <span class="meta-item">{{ formatDate(document?.uploaded_at) }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <el-button @click="showSplitDialog = true" type="primary" v-if="document && canSplit">
          <el-icon><Operation /></el-icon>
          拆分模块
        </el-button>
        <el-button @click="startReview" type="success" v-if="document && canReview">
          <el-icon><Document /></el-icon>
          开始评审
        </el-button>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-container">
      <el-row :gutter="20">
        <!-- 左侧：文档内容 -->
        <el-col :span="16">
          <el-card class="document-content" shadow="never">
            <template #header>
              <div class="content-header">
                <span>文档内容</span>
                <el-button-group size="small">
                  <el-button 
                    :type="viewMode === 'content' ? 'primary' : ''"
                    @click="viewMode = 'content'"
                  >
                    原文
                  </el-button>
                  <el-button 
                    :type="viewMode === 'modules' ? 'primary' : ''"
                    @click="viewMode = 'modules'"
                  >
                    模块视图
                  </el-button>
                </el-button-group>
              </div>
            </template>

            <!-- 原文内容 -->
            <div v-if="viewMode === 'content'" class="original-content">
              <div v-if="document && document.content && document.content.length > 0" class="content-viewer">
                <!-- 文档类型标识和工具栏 -->
                <div class="document-header">
                  <div class="document-type-info">
                    <el-tag :type="getDocumentTypeColor(document.document_type)" size="large">
                      {{ getDocumentTypeName(document.document_type) }}
                    </el-tag>
                    <div class="document-stats">
                      <span class="stat-item">
                        <el-icon><Document /></el-icon>
                        {{ document.word_count }} 字
                      </span>
                      <span class="stat-item">
                        <el-icon><Files /></el-icon>
                        {{ document.page_count }} 页
                      </span>
                      <span class="stat-item">
                        <el-icon><Clock /></el-icon>
                        {{ formatDate(document.uploaded_at) }}
                      </span>
                      <span v-if="document.images && document.images.length > 0" class="stat-item image-count">
                        <el-icon><Picture /></el-icon>
                        {{ document.images.length }} 张图片
                      </span>
                    </div>
                  </div>

                  <div class="document-tools">
                    <el-button-group size="small">
                      <el-button @click="copyContent" :icon="CopyDocument">复制</el-button>
                      <el-button @click="downloadContent" :icon="Download">下载</el-button>
                      <el-button @click="toggleFullscreen" :icon="FullScreen">全屏</el-button>
                    </el-button-group>
                  </div>
                </div>

                <!-- 格式化的文档内容 -->
                <div class="document-content-wrapper" :class="{ 'fullscreen': isFullscreen }">
                  <div class="formatted-content" v-html="formatDocumentContent(document.content, document.images)"></div>
                </div>

                <!-- 图片预览区域 -->
                <div v-if="document.images && document.images.length > 0" class="document-images">
                  <el-divider content-position="left">
                    <el-icon><Picture /></el-icon>
                    文档中的图片 ({{ document.images.length }}张)
                  </el-divider>
                  <div class="images-grid">
                    <el-card
                      v-for="(img, index) in document.images"
                      :key="index"
                      class="image-card"
                      shadow="hover"
                    >
                      <el-image
                        :src="img.base64"
                        :alt="img.description"
                        :preview-src-list="getImagePreviewList()"
                        fit="contain"
                        class="document-image"
                      >
                        <template #error>
                          <div class="image-error">
                            <el-icon><PictureFilled /></el-icon>
                            <span>{{ img.description }}</span>
                          </div>
                        </template>
                      </el-image>
                      <div class="image-info">
                        <span class="image-title">{{ img.description }}</span>
                      </div>
                    </el-card>
                  </div>
                </div>
              </div>

              <el-empty v-else description="暂无文档内容">
                <template #description>
                  <div class="empty-description">
                    <p>文档内容为空或正在处理中</p>
                    <el-button type="primary" @click="reloadDocument">重新加载</el-button>
                  </div>
                </template>
              </el-empty>
            </div>

            <!-- 模块视图 -->
            <div v-else-if="viewMode === 'modules'" class="modules-view">
              <div v-if="modules.length > 0">
                <!-- 模块统计信息 -->
                <div class="modules-header">
                  <div class="modules-stats">
                    <el-statistic title="模块总数" :value="modules.length" />
                    <el-statistic title="平均长度" :value="getAverageModuleLength()" suffix="字符" />
                    <el-statistic title="置信度" :value="getAverageConfidence()" suffix="%" />
                  </div>
                  <div class="modules-actions">
                    <el-button @click="showSplitDialog = true" type="warning" size="small">
                      <el-icon><Operation /></el-icon>
                      重新拆分
                    </el-button>
                  </div>
                </div>
                
                <!-- 模块列表 -->
                <div class="modules-list">
                  <div
                    v-for="(module, index) in modules"
                    :key="module.id"
                    class="module-card"
                    :class="{ active: selectedModuleId === module.id }"
                    @click="selectModule(module)"
                  >
                    <div class="module-header">
                      <div class="module-order-badge">
                        <span class="order-number">{{ module.order_num || (index + 1) }}</span>
                      </div>
                      <div class="module-info">
                        <h4 class="module-title">{{ module.title }}</h4>
                        <div class="module-meta">
                          <el-tag size="small" type="info">
                            {{ module.content_length || module.content?.length || 0 }} 字符
                          </el-tag>
                          <el-tag size="small" :type="getConfidenceType(module.confidence_score)">
                            置信度 {{ Math.round((module.confidence_score || 0) * 100) }}%
                          </el-tag>
                          <el-tag v-if="module.is_auto_generated" size="small" type="success">
                            自动生成
                          </el-tag>
                        </div>
                      </div>
                      <div class="module-actions">
                        <el-button size="small" type="text" @click.stop="viewModuleDetail(module)">
                          <el-icon><View /></el-icon>
                        </el-button>
                        <el-button 
                          size="small" 
                          type="text" 
                          @click.stop="generateTestCasesForModule(module)"
                          title="基于模块生成用例"
                        >
                          <el-icon><MagicStick /></el-icon>
                        </el-button>
                      </div>
                    </div>
                    <div class="module-preview">
                      {{ getModulePreview(module.content) }}
                    </div>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无模块，请先拆分文档">
                <template #description>
                  <div class="empty-description">
                    <p>文档尚未拆分为模块</p>
                    <p class="empty-tip">拆分模块可以帮助您更好地组织和分析需求文档</p>
                  </div>
                </template>
                <el-button type="primary" @click="showSplitDialog = true">
                  <el-icon><Operation /></el-icon>
                  开始拆分模块
                </el-button>
              </el-empty>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：模块详情或操作面板 -->
        <el-col :span="8">
          <!-- 模块详情 -->
          <el-card v-if="selectedModule" class="module-detail" shadow="never">
            <template #header>
              <div class="detail-header">
                <span>模块详情</span>
                <el-button size="small" @click="selectedModule = null">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </template>

            <div class="module-info">
              <h3>{{ selectedModule.title }}</h3>
              <div class="module-meta">
                <div class="meta-row">
                  <span class="label">顺序：</span>
                  <span class="value">第 {{ selectedModule.order_num }} 个模块</span>
                </div>
                <div class="meta-row">
                  <span class="label">内容长度：</span>
                  <span class="value">{{ selectedModule.content?.length || 0 }} 字符</span>
                </div>
                <div class="meta-row">
                  <span class="label">置信度：</span>
                  <span class="value">{{ Math.round((selectedModule.confidence_score || 0) * 100) }}%</span>
                </div>
              </div>

              <div class="module-content">
                <h4>模块内容</h4>
                <div class="content-text">
                  {{ selectedModule.content }}
                </div>
              </div>

              <!-- 模块操作按钮 -->
              <div class="module-actions-panel">
                <el-button 
                  type="primary" 
                  @click="generateTestCasesForModule(selectedModule)"
                  :icon="MagicStick"
                  block
                >
                  基于模块生成用例
                </el-button>
              </div>
            </div>
          </el-card>

          <!-- 操作面板 -->
          <el-card v-else class="action-panel" shadow="never">
            <template #header>
              <span>操作面板</span>
            </template>

            <div class="actions">
              <el-button 
                @click="startReview" 
                type="primary" 
                :disabled="!canReview"
                block
              >
                <el-icon><Document /></el-icon>
                开始评审
              </el-button>
              <el-button 
                @click="viewReviewHistory" 
                type="info"
                block
              >
                <el-icon><View /></el-icon>
                查看评审历史
              </el-button>
              <el-button 
                @click="showSplitDialog = true" 
                type="warning"
                :disabled="!canSplit"
                block
              >
                <el-icon><Operation /></el-icon>
                重新拆分模块
              </el-button>
              <el-button 
                @click="showGenerateTestCasesDialog" 
                type="success"
                :disabled="modules.length === 0"
                block
              >
                <el-icon><MagicStick /></el-icon>
                批量生成用例
              </el-button>
            </div>

            <!-- 文档统计 -->
            <div class="document-stats">
              <h4>文档统计</h4>
              <div class="stats-grid">
                <div class="stat-item">
                  <span class="stat-value">{{ document?.word_count || 0 }}</span>
                  <span class="stat-label">总字数</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">{{ modules.length }}</span>
                  <span class="stat-label">模块数</span>
                </div>
                <div class="stat-item">
                  <span class="stat-value">{{ document?.page_count || 0 }}</span>
                  <span class="stat-label">页数</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 模块拆分对话框 -->
    <ModuleSplitDialog
      v-model="showSplitDialog"
      :document="document"
      :project-id="projectId"
      @success="handleSplitSuccess"
    />

    <!-- AI生成测试用例对话框 -->
    <AIGenerateDialog
      v-model="showGenerateDialog"
      :project-id="projectId"
      :default-module-id="1"
      :initial-source-type="'module'"
      :initial-source-id="selectedModule?.id?.toString()"
      :initial-requirement="getModuleRequirement(selectedModule)"
      @success="onTestCaseGenerated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Operation, Document, View, Close, Files, Clock,
  CopyDocument, Download, FullScreen, MagicStick, Picture, PictureFilled
} from '@element-plus/icons-vue'
import { requirementDocumentApi, type RequirementDocument } from '@/api/aitestrebort/requirements'
import { testcaseApi } from '@/api/aitestrebort/testcase'
import ModuleSplitDialog from './components/ModuleSplitDialog.vue'
import AIGenerateDialog from '@/components/aitestrebort/AIGenerateDialog.vue'

// 路由
const route = useRoute()
const router = useRouter()

// 响应式数据
const document = ref<RequirementDocument | null>(null)
const modules = ref<any[]>([])
const loading = ref(false)
const viewMode = ref<'content' | 'modules'>('content')
const selectedModule = ref<any>(null)
const selectedModuleId = ref<string | null>(null)
const showSplitDialog = ref(false)
const isFullscreen = ref(false)
const showGenerateDialog = ref(false)

// 计算属性
const projectId = computed(() => Number(route.params.projectId))
const documentId = computed(() => route.params.id as string)

const canSplit = computed(() => {
  if (!document.value) return false
  // 只有特定状态才允许拆分模块
  const allowedStatuses = ['uploaded', 'processing', 'ready_for_review', 'failed']
  return allowedStatuses.includes(document.value.status)
})

const canReview = computed(() => {
  if (!document.value) return false
  // 只有ready_for_review状态才允许开始评审
  return document.value.status === 'ready_for_review'
})

// 方法
const loadDocument = async () => {
  loading.value = true
  try {
    const response = await requirementDocumentApi.getDocument(projectId.value, documentId.value)
    
    if (response.data?.status === 200 || response.status === 200) {
      const data = response.data?.data || response.data
      document.value = data
      
      // 总是尝试加载模块列表（不管文档状态如何）
      await loadModules()
    } else {
      ElMessage.error(response.data?.message || response.message || '获取文档详情失败')
    }
  } catch (error) {
    console.error('获取文档详情失败:', error)
    ElMessage.error('获取文档详情失败')
  } finally {
    loading.value = false
  }
}

const reloadDocument = async () => {
  await loadDocument()
}

const loadModules = async () => {
  try {
    const response = await requirementDocumentApi.getModules(projectId.value, documentId.value)
    
    if (response.data?.status === 200 || response.status === 200) {
      const data = response.data?.data || response.data
      modules.value = data.modules || []
      console.log('加载模块列表成功:', modules.value.length, '个模块')
    } else {
      console.warn('获取模块列表失败:', response.data?.message || response.message)
      modules.value = []
    }
  } catch (error) {
    console.error('获取模块列表失败:', error)
    modules.value = []
  }
}

const selectModule = (module: any) => {
  selectedModule.value = module
  selectedModuleId.value = module.id
}

const viewModuleDetail = (module: any) => {
  selectModule(module)
}

const copyContent = async () => {
  if (!document.value?.content) return
  
  try {
    // 检查是否支持现代剪贴板API
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(document.value.content)
      ElMessage.success('内容已复制到剪贴板')
    } else {
      // 回退到传统方法
      if (typeof window !== 'undefined' && window.document) {
        const textArea = window.document.createElement('textarea')
        textArea.value = document.value.content
        textArea.style.position = 'fixed'
        textArea.style.left = '-999999px'
        textArea.style.top = '-999999px'
        window.document.body.appendChild(textArea)
        textArea.focus()
        textArea.select()
        
        try {
          window.document.execCommand('copy')
          ElMessage.success('内容已复制到剪贴板')
        } catch (err) {
          ElMessage.error('复制失败，请手动复制')
        } finally {
          window.document.body.removeChild(textArea)
        }
      } else {
        ElMessage.warning('当前环境不支持复制功能')
      }
    }
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

// 获取图片预览列表
const getImagePreviewList = () => {
  if (!document.value?.images) return []
  return document.value.images.map((img: any) => img.base64).filter(Boolean)
}

const downloadContent = () => {
  if (!document.value?.content) return
  
  try {
    const blob = new Blob([document.value.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    
    // 检查是否在浏览器环境中
    if (typeof window !== 'undefined' && window.document) {
      const a = window.document.createElement('a')
      a.href = url
      a.download = `${document.value.title}.txt`
      window.document.body.appendChild(a)
      a.click()
      window.document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      ElMessage.success('文档已下载')
    } else {
      ElMessage.warning('当前环境不支持文件下载')
    }
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  }
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

const getAverageModuleLength = () => {
  if (modules.value.length === 0) return 0
  const total = modules.value.reduce((sum, module) => sum + (module.content_length || module.content?.length || 0), 0)
  return Math.round(total / modules.value.length)
}

const getAverageConfidence = () => {
  if (modules.value.length === 0) return 0
  const total = modules.value.reduce((sum, module) => sum + (module.confidence_score || 0), 0)
  return Math.round((total / modules.value.length) * 100)
}

const getConfidenceType = (score: number) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
}

const startReview = () => {
  if (!document.value) return
  
  // 跳转到评审页面
  router.push(`/aitestrebort/project/${projectId.value}/requirement-review?documentId=${document.value.id}`)
}

const viewReviewHistory = () => {
  // 跳转到评审历史页面
  router.push(`/aitestrebort/project/${projectId.value}/requirement-review`)
}

const handleSplitSuccess = () => {
  ElMessage.success('模块拆分成功')
  loadDocument()
  viewMode.value = 'modules'
}

const goBack = () => {
  router.back()
}

const getModulePreview = (content: string) => {
  if (!content) return '暂无内容'
  return content.length > 100 ? content.substring(0, 100) + '...' : content
}

const formatDocumentContent = (content: string, images: any[] = []) => {
  if (!content) return ''

  // 调试：查看原始内容前500字符
  console.error('[表格检测] 原始内容前500字符:', content.substring(0, 500))
  console.error('[表格检测] 是否包含【表格】标记:', content.includes('【表格】'))
  console.error('[表格检测] 是否包含 | 字符:', content.includes('|'))

  // 转义HTML特殊字符（完全兼容版本）
  const escapeHtml = (text: string) => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  // 处理表格标记，将【表格】内容提取出来暂存
  let processedContent = content
  const finalTables: string[] = []

  // 方式1: 处理 【表格】...【表格结束】 格式（来自Word文档）
  processedContent = processedContent.replace(/【表格】([\s\S]*?)【表格结束】/g, (match, tableContent) => {
    finalTables.push(tableContent)
    return `__TABLE_PLACEHOLDER_${finalTables.length - 1}__`
  })

  // 方式2: 识别直接用 | 分隔的表格（Markdown格式或没有标记的表格）
  // 将连续的以 | 分隔的行转换为表格格式
  const lines = processedContent.split('\n')
  const newLines: string[] = []
  let inTable = false
  let tableBuffer: string[] = []

  // 调试：统计表格行检测情况
  let totalLines = lines.length
  let detectedTableRows = 0
  let nonTableRows = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmedLine = line.trim()

    // 判断这行是否是表格行（有多个 | 分隔）
    // 表格行可能有 "功能 ID | 功能名称" 格式或 "| 功能 ID | 功能名称" 格式
    const pipeCount = (trimmedLine.match(/\|/g) || []).length
    const isTableRow = pipeCount >= 3 && trimmedLine.includes(' | ')

    // 跳过空行（但如果在表格中则不跳过）
    const isEmptyLine = trimmedLine === ''

    if (isTableRow) {
      detectedTableRows++
      // 是表格行
      if (!inTable) {
        // 开始新表格
        inTable = true
        if (tableBuffer.length > 0) {
          // 先输出之前的非表格内容
          newLines.push(...tableBuffer)
          tableBuffer = []
        }
        tableBuffer.push('__TABLE_START__')
      }
      tableBuffer.push(trimmedLine)
    } else if (!isEmptyLine) {
      // 不是表格行且不是空行（空行在表格中被忽略）
      nonTableRows++
      if (inTable) {
        // 结束当前表格
        tableBuffer.push('__TABLE_END__')
        newLines.push(...tableBuffer)
        tableBuffer = []
        inTable = false
      }
      newLines.push(line)
    }
    // 空行不输出（既不是表格内容也不是正文）
  }

  // 处理末尾可能剩余的表格
  if (inTable && tableBuffer.length > 0) {
    tableBuffer.push('__TABLE_END__')
    newLines.push(...tableBuffer)
  }

  processedContent = newLines.join('\n')
  console.error(`[表格检测] 总行数: ${totalLines}, 检测到表格行: ${detectedTableRows}, 非表格行: ${nonTableRows}`)

  // 从新的标记中提取表格（方式2检测到的）
  processedContent = processedContent.replace(/__TABLE_START__([\s\S]*?)__TABLE_END__/g, (match, tableContent) => {
    finalTables.push(tableContent)
    return `__TABLE_PLACEHOLDER_${finalTables.length - 1}__`
  })

  console.error('识别到的表格数量:', finalTables.length)

  // 转义剩余内容
  let formatted = escapeHtml(processedContent)

  // 处理PDF页面标记
  formatted = formatted.replace(/=== 第 (\d+) 页 ===/g, '<div class="page-marker">📄 第 $1 页</div>')

  // 处理标题
  formatted = formatted.replace(/^### (.+)$/gm, '<h3 class="doc-h3">$1</h3>')
  formatted = formatted.replace(/^## (.+)$/gm, '<h2 class="doc-h2">$1</h2>')
  formatted = formatted.replace(/^# (.+)$/gm, '<h1 class="doc-h1">$1</h1>')

  // 处理数字标题
  formatted = formatted.replace(/^(\d+\.\d+\.\d+)\s+(.+)$/gm, '<h4 class="doc-h4">$1 $2</h4>')
  formatted = formatted.replace(/^(\d+\.\d+)\s+(.+)$/gm, '<h4 class="doc-h4">$1 $2</h4>')
  formatted = formatted.replace(/^(\d+)\.\s*(.+)$/gm, '<h3 class="doc-h3">$1. $2</h3>')

  // 处理特殊格式
  formatted = formatted.replace(/([A-Z]+\d+[-_]\d+[A-Z]*)/g, '<span class="code-highlight">$1</span>')
  formatted = formatted.replace(/(V\d+\.\d+)/g, '<span class="version-tag">$1</span>')

  // 处理URL链接
  formatted = formatted.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="doc-link">$1</a>')

  // 恢复表格并渲染
  finalTables.forEach((tableContent, index) => {
    const rows = tableContent.trim().split('\n').filter(row => row.trim().length > 0)

    let tableHtml = '<div class="document-table"><table class="doc-table">'

    rows.forEach((row, rowIndex) => {
      // 清理行：移除首尾的 | 符号
      const cleanRow = row.trim().replace(/^\|+|\|+$/g, '')
      // 用 | 分隔单元格
      const cells = cleanRow.split('|').map(cell => cell.trim())

      if (rowIndex === 0) {
        // 表头
        tableHtml += '<thead><tr>' + cells.map(cell => `<th>${cell}</th>`).join('') + '</tr></thead><tbody>'
      } else {
        tableHtml += '<tr>' + cells.map(cell => `<td>${cell}</td>`).join('') + '</tr>'
      }
    })

    tableHtml += '</tbody></table></div>'
    formatted = formatted.replace(`__TABLE_PLACEHOLDER_${index}__`, tableHtml)
  })

  // 处理图片占位符 - 将 __IMAGE_N__ 替换为实际图片
  if (images && images.length > 0) {
    // 按图片索引替换占位符
    images.forEach((img, index) => {
      // Word图片格式: __IMAGE_N__
      const wordPlaceholder = `__IMAGE_${index + 1}__`
      // PDF图片格式: __IMAGE_PAGE_N__
      const pdfPlaceholder = `__IMAGE_\\d+_${index + 1}__`

      if (img.base64) {
        const imgHtml = `<div class="inline-image"><img src="${img.base64}" alt="${img.description || '图片'}" class="content-image" /></div>`

        // 替换Word格式占位符
        formatted = formatted.replace(wordPlaceholder, imgHtml)

        // 替换PDF格式占位符（贪婪模式替换所有页面的相同索引图片）
        formatted = formatted.replace(new RegExp(pdfPlaceholder, 'g'), imgHtml)
      }
    })
  }

  // 处理换行和段落
  formatted = formatted.replace(/\n\n/g, '</p><p class="doc-paragraph">')
  formatted = formatted.replace(/\n/g, '<br>')
  formatted = '<p class="doc-paragraph">' + formatted + '</p>'

  // 处理列表项
  formatted = formatted.replace(/<br>(\d+)\. (.+?)(?=<br>|$)/g, '<div class="doc-list-item"><span class="list-number">$1.</span> $2</div>')

  return formatted
}

const getDocumentTypeName = (type: string) => {
  const types: Record<string, string> = {
    'word': 'Word文档',
    'pdf': 'PDF文档',
    'excel': 'Excel文档',
    'text': '文本文档',
    'markdown': 'Markdown文档',
    'unknown': '未知格式'
  }
  return types[type] || type
}

const getDocumentTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    'word': 'primary',
    'pdf': 'danger',
    'excel': 'success',
    'text': 'info',
    'markdown': 'warning',
    'unknown': ''
  }
  return colors[type] || ''
}

// 辅助方法
const formatDate = (dateString: string) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('zh-CN')
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    uploaded: 'info',
    processing: 'warning',
    ready_for_review: 'primary',
    reviewing: 'warning',
    review_completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    uploaded: '已上传',
    processing: '处理中',
    ready_for_review: '待评审',
    reviewing: '评审中',
    review_completed: '评审完成',
    failed: '失败'
  }
  return texts[status] || status
}

const generateTestCasesForModule = (module: any) => {
  // 设置选中的模块并打开生成对话框
  selectedModule.value = module
  selectedModuleId.value = module.id
  showGenerateDialog.value = true
}

const showGenerateTestCasesDialog = () => {
  // 批量生成用例
  if (modules.value.length === 0) {
    ElMessage.warning('没有可用的模块')
    return
  }
  
  // 可以选择第一个模块或者让用户选择
  selectedModule.value = modules.value[0]
  selectedModuleId.value = modules.value[0].id
  showGenerateDialog.value = true
}

const onTestCaseGenerated = (testCases: any[]) => {
  ElMessage.success(`成功生成 ${testCases.length} 个测试用例`)
  // 可以在这里添加其他处理逻辑，比如刷新页面或跳转到测试用例管理页面
}

const getModuleRequirement = (module: any): string => {
  if (!module) return ''
  
  return `基于需求模块"${module.title}"生成测试用例。

模块内容：
${module.content || ''}

请根据上述模块内容生成相应的测试用例，包括正常流程、异常情况和边界条件的测试。`
}

// 创建默认测试用例模块的方法
const createDefaultTestCaseModule = async () => {
  try {
    const response = await testcaseApi.createModule(projectId.value, {
      name: '默认测试用例模块',
      description: '系统自动创建的默认测试用例模块'
    })
    
    if (response.data) {
      return response.data.id
    }
  } catch (error) {
    console.error('创建默认测试用例模块失败:', error)
  }
  return null
}

// 生命周期
onMounted(() => {
  loadDocument()
})
</script>

<style scoped>
.document-detail {
  padding: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.back-btn {
  padding: 8px;
  margin-top: 4px;
}

.title-section {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.document-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-item {
  color: #909399;
  font-size: 14px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.content-container {
  min-height: 600px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.original-content {
  height: 100%;
}

.content-viewer {
  background: #fff;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.document-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.document-type-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.document-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 14px;
}

.document-tools {
  display: flex;
  align-items: center;
}

.document-content-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  max-height: 600px; /* 设置最大高度 */
  border: 1px solid #ebeef5; /* 添加边框以更好地显示滚动区域 */
  border-radius: 4px;
}

.document-content-wrapper.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background: white;
  padding: 40px;
}

.formatted-content {
  line-height: 1.8;
  color: #303133;
  font-size: 15px;
  max-width: none;
}

.formatted-content .page-marker {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 10px 20px;
  margin: 24px 0 20px 0;
  border-radius: 8px;
  font-weight: bold;
  font-size: 15px;
  display: inline-block;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.formatted-content .doc-h1 {
  color: #303133;
  font-size: 28px;
  font-weight: bold;
  margin: 32px 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 3px solid #409eff;
  line-height: 1.3;
}

.formatted-content .doc-h2 {
  color: #409eff;
  font-size: 22px;
  font-weight: bold;
  margin: 28px 0 16px 0;
  padding-left: 16px;
  border-left: 5px solid #409eff;
  line-height: 1.4;
}

.formatted-content .doc-h3 {
  color: #606266;
  font-size: 18px;
  font-weight: bold;
  margin: 20px 0 12px 0;
  line-height: 1.4;
}

.formatted-content .doc-paragraph {
  margin: 16px 0;
  text-align: justify;
  text-indent: 2em;
}

.formatted-content .doc-list-item {
  margin: 10px 0;
  padding-left: 24px;
  position: relative;
  line-height: 1.6;
}

.formatted-content .list-number {
  color: #409eff;
  font-weight: bold;
  position: absolute;
  left: 0;
}

.formatted-content .table-separator {
  color: #dcdfe6;
  margin: 0 6px;
  font-weight: bold;
}

.formatted-content .code-highlight {
  background: #f1f2f6;
  color: #e74c3c;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-weight: bold;
}

.formatted-content .version-tag {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.formatted-content .doc-link {
  color: #409eff;
  text-decoration: none;
  border-bottom: 1px dashed #409eff;
}

.formatted-content .doc-link:hover {
  color: #66b1ff;
  border-bottom-style: solid;
}

.empty-description {
  text-align: center;
}

.empty-description p {
  margin: 8px 0;
  color: #909399;
}

.empty-tip {
  font-size: 12px;
  color: #c0c4cc;
}

.modules-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  max-height: 600px; /* 与文档内容视图保持一致 */
}

.modules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

.modules-stats {
  display: flex;
  gap: 32px;
}

.modules-list {
  flex: 1;
  overflow-y: auto;
  max-height: 600px; /* 设置最大高度 */
  border: 1px solid #ebeef5; /* 添加边框以更好地显示滚动区域 */
  border-radius: 4px;
  padding: 16px 16px 32px 16px; /* 增加底部内边距 */
}

.module-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fff;
}

.module-card:last-child {
  margin-bottom: 24px; /* 为最后一个卡片添加额外的底部边距 */
}

.module-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transform: translateY(-2px);
}

.module-card.active {
  border-color: #409eff;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.module-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.module-order-badge {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.order-number {
  color: white;
  font-weight: bold;
  font-size: 14px;
}

.module-info {
  flex: 1;
}

.module-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  line-height: 1.4;
}

.module-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.module-actions {
  flex-shrink: 0;
}

.module-preview {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin-top: 8px;
  padding-left: 52px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.module-info h3 {
  margin: 0 0 16px 0;
  color: #303133;
}

.module-meta {
  margin-bottom: 16px;
}

.meta-row {
  display: flex;
  margin-bottom: 8px;
}

.meta-row .label {
  font-weight: bold;
  color: #606266;
  min-width: 80px;
}

.meta-row .value {
  color: #303133;
}

.module-content h4 {
  margin: 16px 0 8px 0;
  color: #606266;
  font-size: 14px;
}

.actions {
  margin-bottom: 24px;
}

.actions .el-button {
  margin-bottom: 8px;
}

.document-stats h4 {
  margin: 0 0 16px 0;
  color: #606266;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.module-actions-panel {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

/* 图片预览样式 */
.document-images {
  margin-top: 24px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.document-images .el-divider {
  margin: 0 0 16px 0;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.image-card {
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.image-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.document-image {
  width: 100%;
  height: 200px;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}

.image-error .el-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.image-info {
  padding: 12px;
  background: #fff;
}

.image-title {
  font-size: 13px;
  color: #606266;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-item.image-count {
  color: #67c23a;
  font-weight: 500;
}

/* 内嵌图片样式 */
.inline-image {
  margin: 16px 0;
  text-align: center;
}

.inline-image .content-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  cursor: pointer;
}

.inline-image .content-image:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: scale(1.02);
  transition: all 0.3s ease;
}

/* 文档表格样式 */
.table-wrapper {
  margin: 16px 0;
  overflow-x: auto;
}

.document-table {
  width: 100%;
  margin: 16px 0;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.6;
  background: #fff;
}

.doc-table th,
.doc-table td {
  border: 1px solid #dcdfe6;
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}

.doc-table th {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.doc-table td {
  color: #606266;
}

.doc-table tr:hover td {
  background: #f0f9ff;
}

.doc-table {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.formatted-content .doc-h4 {
  color: #409eff;
  font-size: 16px;
  font-weight: bold;
  margin: 20px 0 10px 0;
  padding-left: 12px;
  border-left: 4px solid #409eff;
  line-height: 1.4;
}
</style>