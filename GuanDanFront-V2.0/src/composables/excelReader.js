/**
 * Excel文件读取工具
 * 用于读取掼蛋比赛报名表
 */

import { read, utils } from "xlsx";

/**
 * 读取Excel文件并解析队伍数据
 * @param {File} file - Excel文件对象
 * @returns {Promise<Array>} - 解析后的队伍数据数组
 */
export async function readExcelFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = async (e) => {
      try {        
        const data = new Uint8Array(e.target.result);
        const workbook = read(data, { type: 'array' });
        
        // 假设数据在第一个工作表中
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        // 将工作表转换为JSON数组
        const jsonData = utils.sheet_to_json(worksheet, { header: 1 });
        // 解析数据
        const teams = parseTeamData(jsonData);
        resolve(teams);
        
        
      } catch (error) {
        reject(new Error(`解析Excel文件失败: ${error.message}`));
      }
    };
    
    reader.onerror = () => {
      reject(new Error('读取文件失败'));
    };
    
    reader.readAsArrayBuffer(file);
  });
}

/**
 * 从URL读取Excel文件
 * @param {string} url - Excel文件URL
 * @returns {Promise<Array>} - 解析后的队伍数据数组
 */
export async function readExcelFromUrl(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const arrayBuffer = await response.arrayBuffer();
    
    const workbook = read(new Uint8Array(arrayBuffer), { type: 'array' });
    
    // 假设数据在第一个工作表中
    const firstSheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[firstSheetName];
    
    // 将工作表转换为JSON数组
    const jsonData = utils.sheet_to_json(worksheet, { header: 1 });
    console.log('🔄 JSON数据转换完成:');
    console.log('  - 总行数:', jsonData.length);
    console.log('  - 前5行数据:');
    jsonData.slice(0, 5).forEach((row, index) => {
      console.log(`    行${index + 1}:`, row);
    });
    
    // 解析数据
    const teams = parseTeamData(jsonData);
    return teams;
    
  } catch (error) {
    throw new Error(`读取Excel文件失败: ${error.message}`);
  }
}

/**
 * 解析Excel数据为队伍信息
 * @param {Array} jsonData - Excel转换的JSON数据
 * @returns {Array} - 标准化的队伍数据
 */
function parseTeamData(jsonData) {
  const teams = [];
  
  // 跳过标题行，从第2行开始处理
  for (let i = 2; i < jsonData.length; i++) {
    const row = jsonData[i];
    
    // 检查行是否有效（至少有办公室信息）
    if (!row || row.length < 2) continue;
    
    const officeNumber = row[1]; // 办公室列
    if (!officeNumber) continue;
    
    let foundTeams = 0;
    
    for (let idx = 0; idx < 4; idx++) {
      // 计算对应列的索引
      // 根据Excel表格结构：小组A(第4列), 队员(第5列), 小组B(第7列), 队员(第8列), 等等
      const teamColumnIndex = 4 + (idx * 3); // A:3, B:6, C:9, D:12
      const levelIndex = teamColumnIndex + 1;
      const membersColumnIndex = teamColumnIndex + 2; // A:4, B:7, C:10, D:13
      
      const teamName = row[teamColumnIndex];
      const level = row[levelIndex];
      const members = row[membersColumnIndex];

      console.log(`    📊 等级${level} (列${teamColumnIndex + 1},${membersColumnIndex + 1}):`, 
                  `队名="${teamName}", 队员="${members}"`);
      
      // 检查是否有队员信息（这是判断队伍是否存在的关键）
      if (members && typeof members === 'string' && members.trim().length > 0) {
        // 解析队员姓名
        const membersList = parseMembers(members);
        console.log(`      👥 解析队员:`, membersList);
        
        if (membersList.length > 1) {
          const team = {
            id: `${officeNumber}-${level}`,
            office: officeNumber.toString(),
            level: level,
            members: membersList,
            teamName: teamName || `${officeNumber}${level}队` // 如果没有队名，生成默认队名
          };
          
          teams.push(team);
          foundTeams++;
          console.log(`      ✅ 添加队伍:`, team);
        } else {
          console.log(`      ⚠️  跳过队伍: 队员解析失败`);
        }
      } else {
        console.log(`      ⚠️  跳过等级${level}: 没有队员信息`);
        // 如果当前等级没有队员信息，检查是否应该继续
        // 有些办公室可能在中间等级留空，但后面还有队伍
      }
    }
    
    console.log(`  📊 办公室${officeNumber}共找到 ${foundTeams} 支队伍`);
  }
  
  console.log(`\n🎯 解析完成，总共创建了 ${teams.length} 个队伍:`);
  
  // 按办公室分组显示结果
  const teamsByOffice = {};
  teams.forEach(team => {
    if (!teamsByOffice[team.office]) {
      teamsByOffice[team.office] = [];
    }
    teamsByOffice[team.office].push(team);
  });
  
  Object.entries(teamsByOffice).forEach(([office, officeTeams]) => {
    console.log(`  🏢 办公室${office} (${officeTeams.length}支队伍):`);
    officeTeams.forEach((team, index) => {
      console.log(`    ${index + 1}. ${team.id}: ${team.members.join('-')} (${team.teamName})`);
    });
  });
  
  return teams;
}

/**
 * 解析队员姓名字符串
 * @param {string} membersStr - 队员姓名字符串
 * @returns {Array} - 队员姓名数组
 */
function parseMembers(membersStr) {
  if (!membersStr || typeof membersStr !== 'string') {
    return [];
  }
  
  // 清理字符串并分割
  const cleanStr = membersStr.trim();
  
  // 尝试不同的分隔符
  let members = [];
  
  if (cleanStr.includes('-')) {
    members = cleanStr.split('-');
  } else if (cleanStr.includes('、')) {
    members = cleanStr.split('、');
  } else if (cleanStr.includes(',')) {
    members = cleanStr.split(',');
  } else if (cleanStr.includes('，')) {
    members = cleanStr.split('，');
  } else if (cleanStr.includes(' ')) {
    members = cleanStr.split(' ');
  } else {
    // 如果没有分隔符，可能是单人队伍
    members = [cleanStr];
  }
  
  // 清理每个队员姓名
  return members
    .map(name => name.trim())
    .filter(name => name.length > 0);
}
/**
 * 验证解析出的队伍数据
 * @param {Array} teams - 队伍数据数组
 * @returns {Object} - 验证结果
 */
export function validateTeamData(teams) {
  console.log('\n🔍 开始验证队伍数据...');
  console.log('📊 队伍总数:', teams.length);
  
  const validation = {
    isValid: true,
    errors: [],
    warnings: [],
    statistics: {
      totalTeams: teams.length,
      officeCount: new Set(teams.map(t => t.office)).size,
      levelDistribution: {},
      officeDistribution: {}
    }
  };
  
  console.log('🏢 办公室数量:', validation.statistics.officeCount);
  
  // 统计等级分布
  teams.forEach(team => {
    if (!validation.statistics.levelDistribution[team.level]) {
      validation.statistics.levelDistribution[team.level] = 0;
    }
    validation.statistics.levelDistribution[team.level]++;
    
    // 统计各办公室队伍数量
    if (!validation.statistics.officeDistribution[team.office]) {
      validation.statistics.officeDistribution[team.office] = 0;
    }
    validation.statistics.officeDistribution[team.office]++;
  });
  
  console.log('📈 等级分布:', validation.statistics.levelDistribution);
  console.log('🏢 办公室队伍分布:', validation.statistics.officeDistribution);
  
  // 检查各办公室队伍情况
  const officeTeams = {};
  teams.forEach(team => {
    if (!officeTeams[team.office]) {
      officeTeams[team.office] = new Set();
    }
    officeTeams[team.office].add(team.level);
  });
  
  console.log('🏢 各办公室队伍详情:');
  Object.entries(officeTeams).forEach(([office, levels]) => {
    const teamCount = validation.statistics.officeDistribution[office];
    console.log(`  办公室${office}: ${teamCount}支队伍 (${Array.from(levels).join(', ')})`);
    
    // 检查队伍数量合理性
    if (teamCount < 2) {
      const warning = `办公室${office}只有${teamCount}支队伍，可能影响分组效果`;
      validation.warnings.push(warning);
      console.log(`    ⚠️  ${warning}`);
    } else if (teamCount > 4) {
      const warning = `办公室${office}有${teamCount}支队伍，超过预期的4支`;
      validation.warnings.push(warning);
      console.log(`    ⚠️  ${warning}`);
    } else {
      console.log(`    ✅ 队伍数量正常`);
    }
  });
  
  // 检查队伍成员数量
  console.log('\n👥 检查队伍成员数量:');
  teams.forEach(team => {
    if (team.members.length === 0) {
      const error = `队伍${team.id}没有成员`;
      validation.errors.push(error);
      validation.isValid = false;
      console.log(`  ❌ ${error}`);
    } else if (team.members.length === 1) {
      const warning = `队伍${team.id}只有1名成员`;
      validation.warnings.push(warning);
      console.log(`  ⚠️  ${warning}`);
    } else if (team.members.length > 2) {
      const warning = `队伍${team.id}有${team.members.length}名成员（超过2人）`;
      validation.warnings.push(warning);
      console.log(`  ⚠️  ${warning}`);
    } else {
      console.log(`  ✅ ${team.id}: ${team.members.join('-')} (${team.members.length}人)`);
    }
  });
  
  // 检查分组可行性
  console.log('\n🎯 分组可行性分析:');
  const totalTeams = teams.length;
  const maxRounds = 3;
  const teamsPerRound = Math.floor(totalTeams / 2) * 2; // 确保是偶数
  
  console.log(`  - 总队伍数: ${totalTeams}`);
  console.log(`  - 每轮可安排: ${teamsPerRound} 支队伍`);
  console.log(`  - 未参与队伍: ${totalTeams - teamsPerRound}`);
  
  if (totalTeams < 4) {
    const error = `队伍数量太少(${totalTeams})，无法进行有效分组`;
    validation.errors.push(error);
    validation.isValid = false;
    console.log(`  ❌ ${error}`);
  } else if (totalTeams % 2 === 1) {
    const warning = `队伍数量为奇数(${totalTeams})，每轮会有1支队伍轮空`;
    validation.warnings.push(warning);
    console.log(`  ⚠️  ${warning}`);
  }
  
  console.log('\n📋 验证结果:');
  console.log('  - 验证通过:', validation.isValid);
  console.log('  - 错误数量:', validation.errors.length);
  console.log('  - 警告数量:', validation.warnings.length);
  
  if (validation.errors.length > 0) {
    console.log('❌ 错误列表:');
    validation.errors.forEach(error => console.log(`    ${error}`));
  }
  
  if (validation.warnings.length > 0) {
    console.log('⚠️  警告列表:');
    validation.warnings.forEach(warning => console.log(`    ${warning}`));
  }
  
  return validation;
}