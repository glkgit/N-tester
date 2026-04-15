<template>
  <div class="aitestrebort-testcase">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-divider direction="vertical" />
        <el-breadcrumb separator="/">
          <el-breadcrumb-item @click="$router.push('/aitestrebort/project')">项目管理</el-breadcrumb-item>
          <el-breadcrumb-item>{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item>XMind 用例存放</el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建用例
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- 左侧模块树 保留 -->
      <el-col :span="6">
        <el-card class="module-tree-card">
          <template #header>
            <div class="card-header">
              <span>用例模块</span>
              <el-button type="text" @click="showModuleDialog = true">
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>
          </template>

          <el-tree
            ref="moduleTreeRef"
            :data="moduleTree"
            :props="treeProps"
            node-key="id"
            :expand-on-click-node="false"
            :highlight-current="true"
            @node-click="handleModuleClick"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <span class="node-label">{{ node.label }}</span>
                <el-dropdown @command="handleModuleAction" trigger="click">
                  <el-button type="text" size="small" @click.stop>
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item :command="{action: 'add', module: data}">添加子模块</el-dropdown-item>
                      <el-dropdown-item :command="{action: 'edit', module: data}">编辑</el-dropdown-item>
                      <el-dropdown-item :command="{action: 'delete', module: data}" divided>删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧XMind用例列表 替换原有测试用例表格 -->
      <el-col :span="18">
        <el-card class="testcase-list-card">
          <!-- 操作栏 -->
          <div class="table-actions">
            <el-button type="primary" @click="handleImportXMind">
              <el-icon><Upload /></el-icon>
              导入XMind
            </el-button>
            <el-button type="success" @click="openAIGenerateDialog">
              <el-icon><MagicStick /></el-icon>
              AI 用例生成(在线模式)
            </el-button>
            <el-button type="info" @click="loadXMindList">
              <el-icon><Refresh /></el-icon>
              刷新列表
            </el-button>
          </div>

          <!-- XMind列表表格 -->
          <div class="table-container">
            <el-table
              :data="xmindList"
              v-loading="loading"
              border
              stripe
              style="width: 100%; min-height: 400px;"
            >
              <el-table-column type="index" label="序号" width="80" align="center" />

              <el-table-column prop="filename" label="文件名" min-width="300">
                <template #default="{ row }">
                  <span style="color: #409eff; cursor: pointer" @click="handlePreview(row)">
                    <i class="el-icon-document" style="margin-right: 5px"></i>
                    {{ row.filename }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column prop="caseCount" label="用例数量" width="120" align="center">
                <template #default="{ row }">
                  <el-tag type="info">{{ row.caseCount }}条</el-tag>
                </template>
              </el-table-column>

              <el-table-column prop="moduleName" label="所属模块" width="150" align="center" />

              <el-table-column prop="createTime" label="生成时间" width="180" align="center" />

              <el-table-column label="操作" width="280" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button size="mini" type="primary" @click="handlePreview(row)">
                    预览
                  </el-button>
                  <el-button size="mini" type="success" @click="handleExportXMind(row)">
                    导出XMind
                  </el-button>
                  <el-button size="mini" type="warning" @click="handleExportExcel(row)">
                    导出Excel
                  </el-button>
                  <el-button size="mini" type="danger" @click="handleDelete(row)">
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 空状态 -->
            <div class="empty-state" v-if="xmindList.length === 0 && !loading">
              <el-empty description="暂无XMind用例文件，可通过AI生成或导入得到">
                <el-button type="primary" @click="goToGenerate" :disabled="!selectedModuleId">
                  去生成测试用例
                </el-button>
              </el-empty>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 预览弹窗 -->
    <el-dialog
      title="XMind用例预览"
      v-model="previewVisible"
      width="70%"
      append-to-body
    >
      <div class="preview-content">
        <el-tree
          :data="previewTree"
          :props="{ label: 'label', children: 'children' }"
          default-expand-all
          highlight-current
        />
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 导入XMind弹窗 -->
    <el-dialog
      title="导入XMind文件"
      v-model="importVisible"
      width="500px"
      append-to-body
    >
      <div class="import-content">
        <el-upload
          ref="upload"
          class="upload-demo"
          drag
          action=""
          :auto-upload="false"
          :limit="1"
          accept=".xmind"
          :on-change="handleFileChange"
          :on-exceed="handleExceed"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
          <div class="el-upload__tip" slot="tip">只能上传.xmind格式的文件</div>
        </el-upload>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmImport" :loading="importLoading">
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建/编辑用例对话框 保留原有 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingTestCase ? '编辑测试用例' : '创建测试用例'"
      width="800px"
      @closed="resetTestCaseForm"
    >
      <el-form
        ref="testcaseFormRef"
        :model="testcaseForm"
        :rules="testcaseFormRules"
        label-width="100px"
      >
        <el-form-item label="用例名称" prop="name">
          <el-input v-model="testcaseForm.name" placeholder="请输入用例名称" />
        </el-form-item>
        <el-form-item label="所属模块" prop="module_id">
          <el-tree-select
            v-model="testcaseForm.module_id"
            :data="moduleTree"
            :props="treeProps"
            placeholder="请选择所属模块"
            clearable
          />
        </el-form-item>
        <el-form-item label="用例等级" prop="level">
          <el-select v-model="testcaseForm.level" placeholder="请选择用例等级">
            <el-option label="P0 - 核心功能" value="P0" />
            <el-option label="P1 - 重要功能" value="P1" />
            <el-option label="P2 - 一般功能" value="P2" />
            <el-option label="P3 - 边缘功能" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item label="前置条件" prop="precondition">
          <el-input
            v-model="testcaseForm.precondition"
            type="textarea"
            :rows="3"
            placeholder="请输入前置条件"
          />
        </el-form-item>
        <el-form-item label="用例描述" prop="description">
          <el-input
            v-model="testcaseForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入用例描述"
          />
        </el-form-item>
        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="testcaseForm.notes"
            type="textarea"
            :rows="2"
            placeholder="请输入备注信息"
          />
        </el-form-item>

        <!-- 测试步骤 -->
        <el-form-item label="测试步骤">
          <div class="test-steps-editor">
            <div
              v-for="(step, index) in testcaseForm.steps"
              :key="index"
              class="step-item"
            >
              <div class="step-header">
                <span class="step-number">步骤 {{ index + 1 }}</span>
                <el-button
                  type="danger"
                  size="small"
                  text
                  @click="removeStep(index)"
                  v-if="testcaseForm.steps.length > 1"
                >
                  删除
                </el-button>
              </div>
              <el-form-item label="操作描述" prop="description">
                <el-input v-model="step.description" type="textarea" :rows="2" />
              </el-form-item>
              <el-form-item label="预期结果" prop="expected_result">
                <el-input v-model="step.expected_result" type="textarea" :rows="2" />
              </el-form-item>
            </div>
            <el-button type="primary" @click="addStep" plain block>
              <el-icon><Plus /></el-icon> 添加步骤
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTestCase">保存</el-button>
      </template>
    </el-dialog>

    <!-- AI生成对话框 保留原有结构，修改成功回调 -->
    <el-dialog
      v-model="showAIGenerateDialog"
      title="AI 生成测试用例"
      width="800px"
      @closed="resetAIGenerateForm"
    >
      <el-form
        ref="aiGenerateFormRef"
        :model="aiGenerateForm"
        :rules="aiGenerateFormRules"
        label-width="100px"
      >
        <el-form-item label="需求导入">
          <div class="requirement-import">
            <el-select
              v-model="selectedRequirementDocument"
              placeholder="从需求文档中选择（可选）"
              style="width: 100%"
              filterable
              clearable
              @change="handleRequirementDocumentChange"
            >
              <el-option
                v-for="doc in requirementDocuments"
                :key="doc.id"
                :label="doc.title"
                :value="doc.id"
              >
                <div class="requirement-option">
                  <span>{{ doc.title }}</span>
                  <el-tag size="small" type="info">{{ getDocumentStatusText(doc.status) }}</el-tag>
                </div>
              </el-option>
            </el-select>
            <div class="import-hint" v-if="requirementDocuments.length === 0">
              <span style="color: #909399; font-size: 12px;">暂无可用需求文档</span>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="需求描述" prop="requirement">
          <el-input
            v-model="aiGenerateForm.requirement"
            type="textarea"
            :rows="6"
            placeholder="请输入需求描述，越详细生成的用例质量越高"
          />
        </el-form-item>
        <el-form-item label="生成数量" prop="count">
          <el-input-number v-model="aiGenerateForm.count" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="上下文信息" prop="context">
          <el-input
            v-model="aiGenerateForm.context"
            type="textarea"
            :rows="3"
            placeholder="可选，输入额外的上下文信息帮助AI更好的理解需求"
          />
        </el-form-item>
        <el-form-item label="选择模型">
          <el-select v-model="aiGenerateForm.llm_config_id" placeholder="请选择LLM模型">
            <el-option
              v-for="config in llmConfigs"
              :key="config.id"
              :label="`${config.name} (${config.provider})`"
              :value="config.id"
            />
          </el-select>
        </el-form-item>
        <!-- 模板选项 -->
        <el-form-item label="模板选项">
          <div class="template-options">
            <div class="template-row">
              <el-checkbox v-model="aiGenerateForm.include_precondition">前置条件</el-checkbox>
              <el-checkbox v-model="aiGenerateForm.include_level">用例等级</el-checkbox>
              <el-checkbox v-model="aiGenerateForm.include_boundary">边界值</el-checkbox>
              <el-checkbox v-model="aiGenerateForm.include_error">异常处理</el-checkbox>
              <el-checkbox v-model="aiGenerateForm.include_compatibility">兼容性</el-checkbox>
            </div>
            <div class="template-row" v-if="aiGenerateForm.include_level">
              <span class="template-label">等级：</span>
              <el-checkbox-group v-model="selectedLevels">
                <el-checkbox label="P0">P0</el-checkbox>
                <el-checkbox label="P1">P1</el-checkbox>
                <el-checkbox label="P2">P2</el-checkbox>
                <el-checkbox label="P3">P3</el-checkbox>
              </el-checkbox-group>
            </div>
            <div class="template-row" v-if="aiGenerateForm.include_compatibility">
              <span class="template-label">兼容性：</span>
              <el-checkbox-group v-model="selectedCompatibilities">
                <el-checkbox label="Web">Web</el-checkbox>
                <el-checkbox label="iOS">iOS</el-checkbox>
                <el-checkbox label="Android">Android</el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <!-- 生成进度条 -->
      <div v-if="generating" class="generate-progress">
        <div class="progress-bar-wrapper">
          <el-progress
            :percentage="progressPercentage"
            :status="progressStatus"
            :indeterminate="progressIndeterminate"
            :duration="6"
            :show-text="false"
          />
          <span class="progress-value">{{ progressPercentage.toFixed(1) }}%</span>
        </div>
        <div class="progress-text">{{ progressText }}</div>
      </div>
      <template #footer>
        <el-button @click="showAIGenerateDialog = false" :disabled="generating">取消</el-button>
        <el-button type="primary" @click="generateTestcase" :loading="generating">
          {{ generating ? '生成中...' : '立即生成' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 模块操作对话框 保留原有 -->
    <el-dialog
      v-model="showModuleDialog"
      :title="editingModule ? '编辑模块' : '创建模块'"
      width="500px"
      @closed="resetModuleForm"
    >
      <el-form
        ref="moduleFormRef"
        :model="moduleForm"
        :rules="moduleFormRules"
        label-width="100px"
      >
        <el-form-item label="模块名称" prop="name">
          <el-input v-model="moduleForm.name" placeholder="请输入模块名称" />
        </el-form-item>
        <el-form-item label="上级模块" prop="parent_id">
          <el-tree-select
            v-model="moduleForm.parent_id"
            :data="moduleTree"
            :props="treeProps"
            placeholder="根模块"
            clearable
          />
        </el-form-item>
        <el-form-item label="模块描述" prop="description">
          <el-input
            v-model="moduleForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入模块描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModuleDialog = false">取消</el-button>
        <el-button type="primary" @click="saveModule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Plus, Search, Refresh, MagicStick, Download, MoreFilled, Upload
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { exportToXMind, parseXMindFile, generatePreviewTree } from '@/utils/xmindUtils'
import { exportToExcel } from '@/utils/exportUtils'
import { testcaseApi } from '@/api/aitestrebort/testcase'
import { aiGeneratorApi } from '@/api/aitestrebort/ai-generator'
import { globalApi } from '@/api/aitestrebort/global'
import { requirementDocumentApi } from '@/api/aitestrebort/requirements'

const route = useRoute()
const projectId = ref(route.params.projectId)
const projectName = ref(route.meta.projectName || '项目')

// 模块树相关
const moduleTreeRef = ref()
const moduleTree = ref([])
const treeProps = {
  children: 'children',
  label: 'name'
}
const selectedModuleId = ref(null)
const selectedModuleName = ref('')

// 模块对话框相关
const showModuleDialog = ref(false)
const editingModule = ref(null)
const moduleFormRef = ref()
const moduleForm = ref({
  name: '',
  parent_id: null,
  description: ''
})
const moduleFormRules = {
  name: [
    { required: true, message: '请输入模块名称', trigger: 'blur' }
  ]
}

// 测试用例对话框相关
const showCreateDialog = ref(false)
const editingTestCase = ref(null)
const testcaseFormRef = ref()
const testcaseForm = ref({
  name: '',
  module_id: null,
  level: 'P1',
  precondition: '',
  description: '',
  notes: '',
  steps: [
    { description: '', expected_result: '' }
  ]
})
const testcaseFormRules = {
  name: [
    { required: true, message: '请输入用例名称', trigger: 'blur' }
  ],
  module_id: [
    { required: true, message: '请选择所属模块', trigger: 'change' }
  ],
  level: [
    { required: true, message: '请选择用例等级', trigger: 'change' }
  ]
}

// AI生成相关
const showAIGenerateDialog = ref(false)
const aiGenerateFormRef = ref()
const generating = ref(false)
const progressPercentage = ref(0)
const progressStatus = ref('')
const progressIndeterminate = ref(true)
const progressDuration = ref(8)
const progressText = ref('正在请求AI生成测试用例，请稍候...')
const aiGenerateForm = ref({
  requirement: '',
  count: 10,
  context: '',
  llm_config_id: null,
  // 模板选项
  include_precondition: true,
  include_level: true,
  levels: 'P0,P1,P2,P3',
  include_compatibility: false,
  compatibility_types: 'Web,iOS,Android',
  include_boundary: true,
  include_error: true
})
const aiGenerateFormRules = {
  requirement: [
    { required: true, message: '请输入需求描述', trigger: 'blur' }
  ]
}
const llmConfigs = ref([])
const requirementDocuments = ref([])
const selectedRequirementDocument = ref(null)

// 模板选项相关
const selectedLevels = ref(['P0', 'P1', 'P2', 'P3'])
const selectedCompatibilities = ref(['Web', 'iOS', 'Android'])

// XMind列表相关
const loading = ref(false)
const xmindList = ref([])
const previewVisible = ref(false)
const previewTree = ref([])
const importVisible = ref(false)
const importLoading = ref(false)
const selectedFile = ref(null)

// 格式化日期函数
const formatDate = (date, format = 'YYYY-MM-DD HH:mm:ss') => {
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  const second = String(d.getSeconds()).padStart(2, '0')

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hour)
    .replace('mm', minute)
    .replace('ss', second)
}

// 加载XMind列表
const loadXMindList = () => {
  const key = `aitestrebort_xmind_list_${projectId.value}`
  const list = localStorage.getItem(key)
  xmindList.value = list ? JSON.parse(list) : []
}

// 保存XMind列表
const saveXMindList = () => {
  const key = `aitestrebort_xmind_list_${projectId.value}`
  localStorage.setItem(key, JSON.stringify(xmindList.value))
}

// 加载模块树
const loadModuleTree = async () => {
  try {
    const res = await testcaseApi.getModuleTree(projectId.value)
    if (res.status === 200) {
      moduleTree.value = res.data
    }
  } catch (error) {
    ElMessage.error('加载模块树失败')
  }
}

// 模块点击
const handleModuleClick = (data) => {
  selectedModuleId.value = data.id
  selectedModuleName.value = data.name
  testcaseForm.value.module_id = data.id
}

// 模块操作
const handleModuleAction = (command) => {
  const { action, module } = command
  if (action === 'add') {
    editingModule.value = null
    moduleForm.value = {
      name: '',
      parent_id: module.id,
      description: ''
    }
    showModuleDialog.value = true
  } else if (action === 'edit') {
    editingModule.value = module
    moduleForm.value = {
      name: module.name,
      parent_id: module.parent_id,
      description: module.description
    }
    showModuleDialog.value = true
  } else if (action === 'delete') {
    ElMessageBox.confirm(
      `确认要删除模块「${module.name}」吗？删除后模块下的所有用例也会被删除。`,
      '提示',
      { type: 'warning' }
    ).then(async () => {
      try {
        await testcaseApi.deleteModule(projectId.value, module.id)
        ElMessage.success('删除成功')
        loadModuleTree()
      } catch (error) {
        ElMessage.error('删除失败')
      }
    })
  }
}

// 保存模块
const saveModule = async () => {
  await moduleFormRef.value.validate()
  try {
    if (editingModule.value) {
      await testcaseApi.updateModule(projectId.value, editingModule.value.id, moduleForm.value)
      ElMessage.success('更新成功')
    } else {
      await testcaseApi.createModule(projectId.value, moduleForm.value)
      ElMessage.success('创建成功')
    }
    showModuleDialog.value = false
    loadModuleTree()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

// 重置模块表单
const resetModuleForm = () => {
  editingModule.value = null
  moduleForm.value = {
    name: '',
    parent_id: null,
    description: ''
  }
  moduleFormRef.value?.resetFields()
}

// 添加测试步骤
const addStep = () => {
  testcaseForm.value.steps.push({ description: '', expected_result: '' })
}

// 删除测试步骤
const removeStep = (index) => {
  testcaseForm.value.steps.splice(index, 1)
}

// 保存测试用例
const saveTestCase = async () => {
  await testcaseFormRef.value.validate()
  try {
    if (editingTestCase.value) {
      await testcaseApi.updateTestCase(projectId.value, editingTestCase.value.id, testcaseForm.value)
      ElMessage.success('更新成功')
    } else {
      await testcaseApi.createTestCase(projectId.value, testcaseForm.value)
      ElMessage.success('创建成功')
    }
    showCreateDialog.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

// 重置测试用例表单
const resetTestCaseForm = () => {
  editingTestCase.value = null
  testcaseForm.value = {
    name: '',
    module_id: selectedModuleId.value,
    level: 'P1',
    precondition: '',
    description: '',
    notes: '',
    steps: [
      { description: '', expected_result: '' }
    ]
  }
  testcaseFormRef.value?.resetFields()
}

// 渲染markdown
const renderMarkdown = (content) => {
  if (!content) return ''
  return marked.parse(content)
}

// 加载LLM配置
const loadLlmConfigs = async () => {
  try {
    const res = await globalApi.getLLMConfigs()
    if (res.status === 200) {
      llmConfigs.value = res.data
      if (res.data.length > 0) {
        const defaultConfig = res.data.find(item => item.is_default) || res.data[0]
        aiGenerateForm.value.llm_config_id = defaultConfig.id
      }
    }
  } catch (error) {
    console.error('加载LLM配置失败:', error)
  }
}

// 加载需求文档列表
const loadRequirementDocuments = async () => {
  try {
    const res = await requirementDocumentApi.getDocuments(projectId.value, {
      page: 1,
      page_size: 100
    })
    if (res.status === 200 && res.data?.items) {
      // 只显示已处理完成的文档
      requirementDocuments.value = res.data.items.filter(doc =>
        doc.status === 'review_completed' || doc.status === 'ready_for_review' || doc.status === 'uploaded'
      )
    }
  } catch (error) {
    console.error('加载需求文档失败:', error)
  }
}

// 打开AI生成对话框
const openAIGenerateDialog = async () => {
  if (!selectedModuleId.value) {
    ElMessage.warning('请先选择左侧模块')
    return
  }
  // 加载需求文档列表
  await loadRequirementDocuments()
  showAIGenerateDialog.value = true
}

// 需求文档选择变化
const handleRequirementDocumentChange = async (documentId) => {
  if (!documentId) {
    selectedRequirementDocument.value = null
    return
  }
  try {
    const res = await requirementDocumentApi.getDocument(projectId.value, documentId)
    if (res.status === 200 && res.data) {
      selectedRequirementDocument.value = res.data
      // 自动填充需求描述
      if (res.data.content) {
        aiGenerateForm.value.requirement = res.data.content
      } else if (res.data.description) {
        aiGenerateForm.value.requirement = res.data.description
      }
    }
  } catch (error) {
    console.error('获取需求文档详情失败:', error)
    ElMessage.error('获取需求文档详情失败')
  }
}

// 获取文档状态文本
const getDocumentStatusText = (status) => {
  const statusMap = {
    'uploaded': '已上传',
    'processing': '处理中',
    'ready_for_review': '待评审',
    'reviewing': '评审中',
    'review_completed': '评审通过',
    'failed': '处理失败',
    'pending': '待处理',
    'completed': '已完成'
  }
  return statusMap[status] || status
}

// 生成测试用例
const generateTestcase = async () => {
  if (!selectedModuleId.value) {
    ElMessage.warning('请先选择左侧模块')
    return
  }
  await aiGenerateFormRef.value.validate()

  // 开始生成，重置进度
  generating.value = true
  progressPercentage.value = 0
  progressIndeterminate.value = false
  progressStatus.value = ''
  progressText.value = '正在请求AI生成测试用例，请稍候...'

  // 目标进度
  const targetProgress = 85
  const duration = 10000 // 10秒内完成到85%
  const startTime = Date.now()
  let animationId

  // 平滑进度动画
  const updateProgress = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min((elapsed / duration) * targetProgress, targetProgress)
    progressPercentage.value = Math.round(progress * 10) / 10 // 保留一位小数

    if (progress < targetProgress - 0.5) {
      animationId = requestAnimationFrame(updateProgress)
    }
  }
  animationId = requestAnimationFrame(updateProgress)

  try {
    // 构建模板选项
    const templateOptions = {
      include_precondition: aiGenerateForm.value.include_precondition,
      include_level: aiGenerateForm.value.include_level,
      levels: selectedLevels.value.join(','),
      include_compatibility: aiGenerateForm.value.include_compatibility,
      compatibility_types: selectedCompatibilities.value.join(','),
      include_boundary: aiGenerateForm.value.include_boundary,
      include_error: aiGenerateForm.value.include_error
    }

    const res = await aiGeneratorApi.generateTestCases(projectId.value, {
      project_id: projectId.value,
      requirement: aiGenerateForm.value.requirement,
      module_id: selectedModuleId.value,
      count: aiGenerateForm.value.count,
      context: aiGenerateForm.value.context,
      llm_config_id: aiGenerateForm.value.llm_config_id,
      ...templateOptions
    })

    // 取消动画，直接设为100%
    cancelAnimationFrame(animationId)
    progressPercentage.value = 100
    progressStatus.value = 'success'
    progressText.value = '生成完成！'

    if (res.status === 200) {
      ElMessage.success('生成成功')
      showAIGenerateDialog.value = false

      // 保存到XMind列表
      const cases = res.data.testcases
      const timestamp = formatDate(new Date(), 'YYYYMMDDHHmmss')
      const filename = `${projectName.value}_${selectedModuleName.value}_${timestamp}.xmind`

      const xmindItem = {
        id: Date.now().toString(),
        filename,
        caseCount: cases.length,
        createTime: formatDate(new Date(), 'YYYY-MM-DD HH:mm:ss'),
        moduleName: selectedModuleName.value,
        projectName: projectName.value,
        rawCases: cases
      }
      xmindList.value.unshift(xmindItem)
      saveXMindList()
    }
  } catch (error) {
    cancelAnimationFrame(animationId)
    progressPercentage.value = 100
    progressStatus.value = 'exception'
    progressText.value = '生成失败'
    ElMessage.error(error.message || '生成失败，请重试')
  } finally {
    setTimeout(() => {
      generating.value = false
      progressPercentage.value = 0
      progressIndeterminate.value = true
      progressStatus.value = ''
    }, 1500)
  }
}

// 重置AI生成表单
const resetAIGenerateForm = () => {
  aiGenerateForm.value = {
    requirement: '',
    count: 10,
    context: '',
    llm_config_id: llmConfigs.value.length > 0 ? (llmConfigs.value.find(item => item.is_default) || llmConfigs.value[0])?.id : null,
    // 模板选项
    include_precondition: true,
    include_level: true,
    levels: 'P0,P1,P2,P3',
    include_compatibility: false,
    compatibility_types: 'Web,iOS,Android',
    include_boundary: true,
    include_error: true
  }
  selectedLevels.value = ['P0', 'P1', 'P2', 'P3']
  selectedCompatibilities.value = ['Web', 'iOS', 'Android']
  aiGenerateFormRef.value?.resetFields()
}

// XMind功能
const handleImportXMind = () => {
  if (!selectedModuleId.value) {
    ElMessage.warning('请先选择左侧模块')
    return
  }
  importVisible.value = true
  selectedFile.value = null
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleExceed = () => {
  ElMessage.warning('只能上传一个XMind文件')
}

const confirmImport = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择要导入的XMind文件')
    return
  }
  importLoading.value = true
  try {
    const cases = await parseXMindFile(selectedFile.value)
    const timestamp = formatDate(new Date(), 'YYYYMMDDHHmmss')
    const filename = `${projectName.value}_${selectedModuleName.value}_${timestamp}.xmind`

    const xmindItem = {
      id: Date.now().toString(),
      filename,
      caseCount: cases.length,
      createTime: formatDate(new Date(), 'YYYY-MM-DD HH:mm:ss'),
      moduleName: selectedModuleName.value,
      projectName: projectName.value,
      rawCases: cases
    }
    xmindList.value.unshift(xmindItem)
    saveXMindList()
    ElMessage.success('导入成功')
    importVisible.value = false
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请检查XMind文件格式是否正确')
  } finally {
    importLoading.value = false
  }
}

const handlePreview = (row) => {
  previewTree.value = generatePreviewTree(row.rawCases, row.moduleName)
  previewVisible.value = true
}

const handleExportXMind = (row) => {
  exportToXMind(row.rawCases, row.filename, row.moduleName)
  ElMessage.success('导出成功')
}

const handleExportExcel = (row) => {
  const excelFilename = row.filename.replace('.xmind', '.xlsx')
  exportToExcel(row.rawCases, excelFilename)
  ElMessage.success('导出成功')
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确认要删除文件「${row.filename}」吗？删除后无法恢复。`,
    '提示',
    { type: 'warning' }
  ).then(() => {
    const index = xmindList.value.findIndex(item => item.id === row.id)
    if (index > -1) {
      xmindList.value.splice(index, 1)
      saveXMindList()
      ElMessage.success('删除成功')
    }
  })
}

const goToGenerate = () => {
  showAIGenerateDialog.value = true
}

// 页面加载
onMounted(async () => {
  await loadModuleTree()
  await loadLlmConfigs()
  loadXMindList()
})
</script>

<style scoped lang="scss">
.aitestrebort-testcase {
  height: 100%;
  width: 100%;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-shrink: 0;

  .header-right {
    flex-shrink: 0;
  }
}

.module-tree-card {
  height: calc(100vh - 140px);
  overflow-y: auto;
  .tree-node {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
}

.testcase-list-card {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
  .table-actions {
    margin-bottom: 20px;
    .el-button {
      margin-right: 10px;
    }
  }
  .table-container {
    flex: 1;
    overflow-y: auto;
    .empty-state {
      margin-top: 100px;
    }
  }
}

.preview-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 10px;
}

.import-content {
  padding: 20px 0;
}

.test-steps-editor {
  width: 100%;
  .step-item {
    margin-bottom: 15px;
    padding: 15px;
    border: 1px solid #eee;
    border-radius: 4px;
    .step-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      font-weight: bold;
    }
  }
}

.template-options {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;

  .template-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
    margin-bottom: 10px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .template-label {
    font-size: 14px;
    color: #606266;
    min-width: 50px;
  }
}

.generate-progress {
  padding: 10px 20px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 10px;

  .progress-bar-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;

    .el-progress {
      flex: 1;
    }

    .progress-value {
      font-size: 14px;
      font-weight: 500;
      color: #303133;
      min-width: 50px;
      text-align: right;
    }
  }

  .progress-text {
    text-align: center;
    font-size: 13px;
    color: #606266;
    margin-top: 8px;
  }
}
</style>
