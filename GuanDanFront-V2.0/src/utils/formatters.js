/**
 * 格式化队伍成员姓名
 * @param {string} teamMembers - 队伍成员字符串，用"-"分隔
 * @returns {string} 格式化后的队伍成员姓名，用换行符分隔
 */
export const formatTeamMembers = (teamMembers) => {
  return teamMembers.replace("-", "\n")
}

/**
 * 延迟函数
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise} Promise对象
 */
export const delay = (ms) => new Promise((res) => setTimeout(res, ms))

/**
 * 检查是否为有效的轮次数据
 * @param {any} data - 需要检查的数据
 * @returns {boolean} 是否有效
 */
export const isValidTurnData = (data) => {
  return data && data.error !== "invalid turn"
}

/**
 * 安全获取数组切片
 * @param {Array} array - 原数组
 * @param {number} start - 开始索引
 * @param {number} end - 结束索引
 * @returns {Array} 切片后的数组
 */
export const safeSlice = (array, start = 0, end) => {
  if (!Array.isArray(array)) return []
  return array.slice(start, end)
}
