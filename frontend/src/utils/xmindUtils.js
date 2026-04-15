import XMind from 'xmind'
import JSZip from 'jszip'
import { saveAs } from 'file-saver'

/**
 * 将测试用例转换为XMind文件并下载
 * @param {Array} cases 测试用例列表
 * @param {String} filename 下载文件名
 * @param {String} moduleName 模块名称
 */
export const exportToXMind = async (cases, filename, moduleName = '测试用例') => {
  const workbook = new XMind.Workbook()
  const sheet = workbook.createSheet({ title: moduleName })
  const rootTopic = sheet.createRootTopic({ title: moduleName })

  // 按用例等级分组
  const levelGroups = {
    P0: rootTopic.addTopic({ title: 'P0 核心功能用例' }),
    P1: rootTopic.addTopic({ title: 'P1 重要功能用例' }),
    P2: rootTopic.addTopic({ title: 'P2 一般功能用例' }),
    P3: rootTopic.addTopic({ title: 'P3 边缘功能用例' })
  }

  cases.forEach(caseItem => {
    const caseTopic = levelGroups[caseItem.level] || levelGroups.P1
    const caseNode = caseTopic.addTopic({ title: caseItem.name })

    // 前置条件
    if (caseItem.precondition) {
      caseNode.addTopic({ title: `前置条件：${caseItem.precondition}` })
    }

    // 测试步骤
    const stepsTopic = caseNode.addTopic({ title: '测试步骤' })
    caseItem.steps.forEach(step => {
      stepsTopic.addTopic({
        title: `${step.step_number}. ${step.description}\n预期结果：${step.expected_result}`
      })
    })

    // 备注
    if (caseItem.notes) {
      caseNode.addTopic({ title: `备注：${caseItem.notes}` })
    }
  })

  // 生成文件并下载
  const buffer = await workbook.toBuffer()
  const blob = new Blob([buffer], { type: 'application/xmind' })
  saveAs(blob, filename)
  return buffer
}

/**
 * 解析XMind文件为测试用例结构
 * @param {File} file XMind文件对象
 * @returns {Promise<Array>} 测试用例列表
 */
export const parseXMindFile = async (file) => {
  const zip = await JSZip.loadAsync(file)
  const contentXml = await zip.file('content.xml').async('string')

  // 简单XML解析提取用例（实际项目可完善解析逻辑）
  const parser = new DOMParser()
  const xmlDoc = parser.parseFromString(contentXml, 'text/xml')
  const topics = xmlDoc.querySelectorAll('topic')

  const cases = []
  // 这里实现XMind内容解析逻辑，根据实际XMind结构调整
  // 简单示例：提取所有叶子节点作为用例
  topics.forEach(topic => {
    const title = topic.querySelector('title')?.textContent
    if (title && title.includes('用例')) {
      cases.push({
        name: title,
        level: 'P1',
        precondition: '',
        steps: [
          {
            step_number: 1,
            description: '执行操作',
            expected_result: '验证结果'
          }
        ],
        notes: '从XMind导入'
      })
    }
  })

  return cases.length > 0 ? cases : [
    {
      name: '导入的测试用例',
      level: 'P1',
      precondition: '系统正常运行',
      steps: [
        { step_number: 1, description: '执行操作', expected_result: '结果符合预期' }
      ],
      notes: '从XMind文件导入'
    }
  ]
}

/**
 * 生成预览用的树形结构数据
 * @param {Array} cases 测试用例列表
 * @param {String} moduleName 模块名称
 * @returns {Array} 树形结构数据
 */
export const generatePreviewTree = (cases, moduleName = '测试用例') => {
  const tree = [{
    label: moduleName,
    children: [
      { label: 'P0 核心功能用例', children: [] },
      { label: 'P1 重要功能用例', children: [] },
      { label: 'P2 一般功能用例', children: [] },
      { label: 'P3 边缘功能用例', children: [] }
    ]
  }]

  cases.forEach(caseItem => {
    const levelIndex = { P0: 0, P1: 1, P2: 2, P3: 3 }[caseItem.level] || 1
    const caseNode = {
      label: caseItem.name,
      children: [
        { label: `前置条件：${caseItem.precondition || '无'}` },
        {
          label: '测试步骤',
          children: caseItem.steps.map(step => ({
            label: `${step.step_number}. ${step.description} → 预期：${step.expected_result}`
          }))
        }
      ]
    }
    if (caseItem.notes) {
      caseNode.children.push({ label: `备注：${caseItem.notes}` })
    }
    tree[0].children[levelIndex].children.push(caseNode)
  })

  return tree
}
