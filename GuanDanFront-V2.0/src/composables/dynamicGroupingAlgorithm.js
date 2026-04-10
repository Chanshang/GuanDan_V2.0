/**
 * 动态掼蛋比赛分组算法
 * 从Excel文件读取数据并生成分组
 */

import { readExcelFromUrl, validateTeamData } from './excelReader.js';

/**
 * 检查两个队伍是否可以对战
 * @param {Object} team1 - 队伍1
 * @param {Object} team2 - 队伍2
 * @returns {boolean} - 是否可以对战
 */
function canMatch(team1, team2) {
  // 不能是同一个办公室
  return team1.office !== team2.office;
}

/**
 * 检查队伍是否已经对战过指定等级
 * @param {string} teamId - 队伍ID
 * @param {string} level - 等级
 * @param {Array} previousMatches - 之前的对战记录
 * @param {Array} teams - 所有队伍数据
 * @returns {boolean} - 是否已经对战过
 */
function hasPlayedAgainstLevel(teamId, level, previousMatches, teams) {
  return previousMatches.some(round => 
    round.some(match => {
      const [, team1Id, , team2Id] = match;
      if (team1Id === teamId) {
        const opponent = teams.find(t => t.id === team2Id);
        return opponent && opponent.level === level;
      }
      if (team2Id === teamId) {
        const opponent = teams.find(t => t.id === team1Id);
        return opponent && opponent.level === level;
      }
      return false;
    })
  );
}

/**
 * 检查两个队伍是否已经对战过
 * @param {string} team1Id - 队伍1 ID
 * @param {string} team2Id - 队伍2 ID
 * @param {Array} previousMatches - 之前的对战记录
 * @returns {boolean} - 是否已经对战过
 */
function hasPlayedBefore(team1Id, team2Id, previousMatches) {
  return previousMatches.some(round => 
    round.some(match => {
      const [, matchTeam1, , matchTeam2] = match;
      return (matchTeam1 === team1Id && matchTeam2 === team2Id) ||
             (matchTeam1 === team2Id && matchTeam2 === team1Id);
    })
  );
}

/**
 * 获取队伍还需要对战的等级
 * @param {string} teamId - 队伍ID
 * @param {Array} previousMatches - 之前的对战记录
 * @param {Array} teams - 所有队伍数据
 * @returns {Array} - 还需要对战的等级数组
 */
function getMissingLevels(teamId, previousMatches, teams) {
  const allLevels = ['A', 'B', 'C'];
  const currentTeam = teams.find(t => t.id === teamId);
  
  if (!currentTeam) return [];
  
  // 过滤掉自己的等级
  const targetLevels = allLevels.filter(level => level !== currentTeam.level);
  
  return targetLevels.filter(level => 
    !hasPlayedAgainstLevel(teamId, level, previousMatches, teams)
  );
}

/**
 * 计算匹配分数
 * @param {Object} team1 - 队伍1
 * @param {Object} team2 - 队伍2
 * @param {Array} previousMatches - 之前的对战记录
 * @param {Array} teams - 所有队伍数据
 * @returns {number} - 匹配分数
 */
function calculateMatchScore(team1, team2, previousMatches, teams) {
  let score = 0;
  
  // 基础分数
  score += 1;
  
  // 不同办公室加分
  if (team1.office !== team2.office) {
    score += 5;
  }
  
  // 等级需求匹配加分
  const team1Missing = getMissingLevels(team1.id, previousMatches, teams);
  const team2Missing = getMissingLevels(team2.id, previousMatches, teams);
  
  if (team1Missing.includes(team2.level)) {
    score += 3;
  }
  
  if (team2Missing.includes(team1.level)) {
    score += 3;
  }
  
  // 都需要对方等级，额外加分
  if (team1Missing.includes(team2.level) && team2Missing.includes(team1.level)) {
    score += 2;
  }
  
  return score;
}


/**
 * 生成一轮匹配 - 改进版本，最大化匹配数量
 * @param {Array} availableTeams - 可用队伍列表
 * @param {Array} previousMatches - 之前的对战记录
 * @param {number} roundNumber - 轮次号
 * @returns {Array} - 本轮匹配结果
 */
function generateRound(availableTeams, previousMatches, roundNumber) {
  const matches = [];
  const usedTeams = new Set();
  const remainingTeams = [...availableTeams];
  
  console.log(`\n开始生成第${roundNumber}轮，可用队伍数: ${remainingTeams.length}`);
  
  // 第一阶段：尝试不同办公室之间的最佳匹配
  console.log('第一阶段：优先匹配不同办公室队伍...');
  
  // 按照还需要对战的等级数排序，优先安排需求多的队伍
  remainingTeams.sort((a, b) => {
    const aMissing = getMissingLevels(a.id, previousMatches, availableTeams);
    const bMissing = getMissingLevels(b.id, previousMatches, availableTeams);
    return bMissing.length - aMissing.length;
  });
  
  for (let i = 0; i < remainingTeams.length; i++) {
    const team1 = remainingTeams[i];
    
    if (usedTeams.has(team1.id)) continue;
    
    let bestOpponent = null;
    let bestScore = -1;
    
    // 寻找最佳对手（不同办公室）
    for (let j = i + 1; j < remainingTeams.length; j++) {
      const team2 = remainingTeams[j];
      
      if (usedTeams.has(team2.id)) continue;
      
      // 第一阶段只考虑不同办公室
      if (!canMatch(team1, team2, false)) continue;
      
      // 如果已经对战过，跳过
      if (hasPlayedBefore(team1.id, team2.id, previousMatches)) continue;
      
      // 计算匹配分数
      const score = calculateMatchScore(team1, team2, previousMatches, availableTeams);
      
      if (score > bestScore) {
        bestScore = score;
        bestOpponent = team2;
      }
    }
    
    if (bestOpponent) {
      const tableNumber = matches.length + 1;
      matches.push([
        `桌${tableNumber}`,
        team1.id,
        team1.members.join('-'),
        bestOpponent.id,
        bestOpponent.members.join('-')
      ]);
      
      usedTeams.add(team1.id);
      usedTeams.add(bestOpponent.id);
      
      console.log(`匹配成功: ${team1.id}(${team1.office}-${team1.level}) vs ${bestOpponent.id}(${bestOpponent.office}-${bestOpponent.level})`);
    }
  }
  
  console.log(`第一阶段完成，已匹配 ${matches.length} 场比赛，剩余 ${availableTeams.length - usedTeams.size} 支队伍`);
  
  // 第二阶段：为剩余队伍匹配（允许同办公室）
  if (usedTeams.size < availableTeams.length) {
    console.log('第二阶段：为剩余队伍匹配（允许同办公室）...');
    
    const unusedTeams = remainingTeams.filter(team => !usedTeams.has(team.id));
    
    for (let i = 0; i < unusedTeams.length; i++) {
      const team1 = unusedTeams[i];
      
      if (usedTeams.has(team1.id)) continue;
      
      let bestOpponent = null;
      let bestScore = -1;
      
      // 寻找最佳对手（允许同办公室）
      for (let j = i + 1; j < unusedTeams.length; j++) {
        const team2 = unusedTeams[j];
        
        if (usedTeams.has(team2.id)) continue;
        
        // 允许同办公室匹配
        if (!canMatch(team1, team2, true)) continue;
        
        // 计算匹配分数
        const score = calculateMatchScore(team1, team2, previousMatches, availableTeams);
        
        if (score > bestScore) {
          bestScore = score;
          bestOpponent = team2;
        }
      }
      
      if (bestOpponent) {
        const tableNumber = matches.length + 1;
        matches.push([
          `桌${tableNumber}`,
          team1.id,
          team1.members.join('-'),
          bestOpponent.id,
          bestOpponent.members.join('-')
        ]);
        
        usedTeams.add(team1.id);
        usedTeams.add(bestOpponent.id);
        
        console.log(`补充匹配: ${team1.id}(${team1.office}-${team1.level}) vs ${bestOpponent.id}(${bestOpponent.office}-${bestOpponent.level}) [同办公室]`);
      }
    }
  }
  
  console.log(`第${roundNumber}轮生成完成: ${matches.length} 场比赛，${availableTeams.length - usedTeams.size} 支队伍轮空`);
  
  return matches;
}

/**
 * 生成分组统计报告
 * @param {Array} teams - 队伍列表
 * @param {Array} allMatches - 所有比赛记录
 * @returns {Object} - 统计报告
 */
function generateReport(teams, allMatches) {
  const report = {
    totalTeams: teams.length,
    totalMatches: allMatches.flat().length,
    teamStatistics: {},
    violationCount: {
      sameOffice: 0,
      repeatedMatch: 0,
      missingLevels: 0
    }
  };
  
  // 统计每个队伍的对战情况
  teams.forEach(team => {
    const stats = {
      matchCount: 0,
      opponents: [],
      levelsPlayed: new Set(),
      missingLevels: []
    };
    
    allMatches.forEach(round => {
      round.forEach(match => {
        const [, team1Id, , team2Id] = match;
        let opponent = null;
        
        if (team1Id === team.id) {
          opponent = teams.find(t => t.id === team2Id);
          stats.matchCount++;
          stats.opponents.push(team2Id);
        } else if (team2Id === team.id) {
          opponent = teams.find(t => t.id === team1Id);
          stats.matchCount++;
          stats.opponents.push(team1Id);
        }
        
        if (opponent) {
          stats.levelsPlayed.add(opponent.level);
          
          // 检查是否同办公室
          if (team.office === opponent.office) {
            report.violationCount.sameOffice++;
          }
        }
      });
    });
    
    // 计算缺失的等级
    const allLevels = ['A', 'B', 'C'];
    const targetLevels = allLevels.filter(level => level !== team.level);
    stats.missingLevels = targetLevels.filter(level => !stats.levelsPlayed.has(level));
    
    if (stats.missingLevels.length > 0) {
      report.violationCount.missingLevels++;
    }
    
    stats.levelsPlayed = Array.from(stats.levelsPlayed);
    report.teamStatistics[team.id] = stats;
  });
  
  // 检查重复对战
  const matchPairs = new Set();
  allMatches.forEach(round => {
    round.forEach(match => {
      const [, team1Id, , team2Id] = match;
      const pair = [team1Id, team2Id].sort().join('-');
      
      if (matchPairs.has(pair)) {
        report.violationCount.repeatedMatch++;
      } else {
        matchPairs.add(pair);
      }
    });
  });
  
  return report;
}

/**
 * 从Excel文件生成完整的三轮分组
 * @param {string} excelFilePath - Excel文件路径或URL
 * @returns {Promise<Object>} - 包含三轮分组结果和统计信息
 */
export async function generateGuandanGroupsFromExcel(excelFilePath) {
  try {
    console.log('正在读取Excel文件...');
    
    // 读取Excel文件
    const teams = await readExcelFromUrl(excelFilePath);
    
    console.log(`成功读取${teams.length}个队伍`);
    
    // 验证数据
    const validation = validateTeamData(teams);
    
    if (!validation.isValid) {
      throw new Error(`数据验证失败: ${validation.errors.join(', ')}`);
    }
    
    if (validation.warnings.length > 0) {
      console.warn('数据警告:', validation.warnings);
    }
    
    // 过滤掉空队伍
    const validTeams = teams.filter(team => team.members.length > 0);
    
    console.log(`有效队伍数: ${validTeams.length}`);
    console.log('队伍分布:', validTeams.reduce((acc, team) => {
      const key = `${team.office}办公室-${team.level}级`;
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {}));
    
    const allMatches = [];
    
    // 生成三轮比赛
    for (let round = 1; round <= 3; round++) {
      console.log(`\n${'='.repeat(50)}`);
      console.log(`生成第${round}轮分组`);
      console.log(`${'='.repeat(50)}`);
      
      const roundMatches = generateRound(validTeams, allMatches, round);
      allMatches.push(roundMatches);
      
      console.log(`第${round}轮共${roundMatches.length}场比赛`);
    }
    
    // 生成统计报告
    const report = generateReport(validTeams, allMatches);
    
    console.log('\n' + '='.repeat(50));
    console.log('最终统计');
    console.log('='.repeat(50));
    console.log(`总队伍数: ${report.totalTeams}`);
    console.log(`总比赛数: ${report.totalMatches}`);
    console.log(`同办公室对战: ${report.violationCount.sameOffice}次`);
    console.log(`重复对战: ${report.violationCount.repeatedMatch}次`);
    console.log(`未完成等级要求: ${report.violationCount.missingLevels}个队伍`);
    
    return {
      rounds: allMatches,
      statistics: report,
      teams: validTeams,
      validation: validation
    };
    
  } catch (error) {
    console.error('生成分组失败:', error);
    throw error;
  }
}
/**
 * 从文件输入生成分组
 * @param {File} file - 用户选择的Excel文件
 * @returns {Promise<Object>} - 分组结果
 */
export async function generateGuandanGroupsFromFile(file) {
  try {
    console.log('正在读取用户上传的Excel文件...');
    
    // 动态导入Excel读取器
    const { readExcelFile } = await import('./excelReader.js');
    
    // 读取Excel文件
    const teams = await readExcelFile(file);
    
    console.log(`成功读取${teams.length}个队伍`);
    
    // 验证数据
    const validation = validateTeamData(teams);
    
    if (!validation.isValid) {
      throw new Error(`数据验证失败: ${validation.errors.join(', ')}`);
    }
    
    if (validation.warnings.length > 0) {
      console.warn('数据警告:', validation.warnings);
    }
    
    // 过滤掉空队伍
    const validTeams = teams.filter(team => team.members.length > 0);
    
    console.log(`有效队伍数: ${validTeams.length}`);
    
    const allMatches = [];
    
    // 生成三轮比赛
    for (let round = 1; round <= 3; round++) {
      console.log(`\n=== 生成第${round}轮分组 ===`);
      
      const roundMatches = generateRound(validTeams, allMatches, round);
      allMatches.push(roundMatches);
      
      console.log(`第${round}轮共${roundMatches.length}场比赛`);
    }
    
    // 生成统计报告
    const report = generateReport(validTeams, allMatches);
    
    return {
      rounds: allMatches,
      statistics: report,
      teams: validTeams,
      validation: validation
    };
    
  } catch (error) {
    console.error('生成分组失败:', error);
    throw error;
  }
}

/**
 * 打印详细的分组结果
 * @param {Object} result - 分组结果
 */
export function printGroupingResult(result) {
  const { rounds, statistics, teams, validation } = result;
  
  console.log('\n' + '='.repeat(50));
  console.log('掼蛋比赛分组结果（从Excel读取）');
  console.log('='.repeat(50));
  
  // 打印数据验证信息
  console.log('\n数据验证信息:');
  console.log(`总队伍数: ${validation.statistics.totalTeams}`);
  console.log(`办公室数: ${validation.statistics.officeCount}`);
  console.log(`等级分布:`, validation.statistics.levelDistribution);
  
  if (validation.warnings.length > 0) {
    console.log('\n警告信息:');
    validation.warnings.forEach(warning => console.log(`⚠️  ${warning}`));
  }
  
  // 打印每轮比赛
  rounds.forEach((round, index) => {
    console.log(`\n第${index + 1}轮比赛 (${round.length}场):`);
    console.log('-'.repeat(30));
    
    round.forEach(match => {
      const [table, team1Id, team1Members, team2Id, team2Members] = match;
      const team1 = teams.find(t => t.id === team1Id);
      const team2 = teams.find(t => t.id === team2Id);
      
      console.log(`${table}: ${team1Id}(${team1.office}-${team1.level}) vs ${team2Id}(${team2.office}-${team2.level})`);
      console.log(`      ${team1Members} vs ${team2Members}`);
    });
  });
  
  // 打印统计信息
  console.log('\n' + '='.repeat(50));
  console.log('统计报告');
  console.log('='.repeat(50));
  console.log(`有效队伍数: ${statistics.totalTeams}`);
  console.log(`总比赛数: ${statistics.totalMatches}`);
  console.log(`违规统计:`);
  console.log(`  同办公室对战: ${statistics.violationCount.sameOffice}次`);
  console.log(`  重复对战: ${statistics.violationCount.repeatedMatch}次`);
  console.log(`  未完成等级要求: ${statistics.violationCount.missingLevels}个队伍`);
}