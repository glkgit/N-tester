import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'

/**
 * 导出测试用例为Excel
 * @param {Array} cases 测试用例列表
 * @param {String} filename 下载文件名
 */
export const exportToExcel = (cases, filename) => {
  const excelData = cases.map(caseItem => ({
    '用例名称': caseItem.name,
    '用例等级': caseItem.level,
    '前置条件': caseItem.precondition || '无',
    '测试步骤': caseItem.steps.map(step => `${step.step_number}. ${step.description}`).join('\n'),
    '预期结果': caseItem.steps.map(step => step.expected_result).join('\n'),
    '备注': caseItem.notes || '无'
  }))

  const worksheet = XLSX.utils.json_to_sheet(excelData)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例')

  // 设置列宽
  const wscols = [
    { wch: 30 }, // 用例名称
    { wch: 10 }, // 等级
    { wch: 40 }, // 前置条件
    { wch: 60 }, // 测试步骤
    { wch: 60 }, // 预期结果
    { wch: 30 } // 备注
  ]
  worksheet['!cols'] = wscols

  const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([excelBuffer], { type: 'application/octet-stream' })
  saveAs(blob, filename)
}
