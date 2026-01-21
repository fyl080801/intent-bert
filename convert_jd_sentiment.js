const fs = require('fs');
const path = require('path');

// CSV文件路径
const csvFilePath = 'datasets/jd_sentiment/train.csv';
// 输出JSON文件路径
const outputPath = 'jd_sentiment_converted.json';

// 读取CSV文件
function readCSV(filePath) {
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.trim().split('\n');
    
    // 跳过标题行
    const dataLines = lines.slice(1);
    
    return dataLines.map(line => {
        // 处理包含逗号的复杂情况
        const parts = [];
        let current = '';
        let inQuotes = false;
        
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                parts.push(current);
                current = '';
            } else {
                current += char;
            }
        }
        parts.push(current);
        
        return {
            sentence: parts[0] ? parts[0].trim() : '',
            label: parseInt(parts[1]) || 0,
            dataset: parts[2] ? parts[2].trim() : 'jd'
        };
    });
}

// 转换数据格式
function convertData(csvData) {
    const result = {};
    
    csvData.forEach((item, index) => {
        const id = (index + 1).toString();
        const sentiment = item.label === 1 ? '正' : '负';
        
        result[id] = {
            id: id,
            records: {
                情感: [sentiment]
            },
            content: item.sentence
        };
    });
    
    return result;
}

// 主函数
function main() {
    try {
        console.log('开始读取CSV文件...');
        const csvData = readCSV(csvFilePath);
        console.log(`成功读取 ${csvData.length} 条记录`);
        
        console.log('开始转换数据格式...');
        const convertedData = convertData(csvData);
        console.log(`成功转换 ${Object.keys(convertedData).length} 条记录`);
        
        console.log('开始写入JSON文件...');
        const jsonContent = JSON.stringify(convertedData, null, 2);
        fs.writeFileSync(outputPath, jsonContent, 'utf-8');
        
        console.log(`转换完成！输出文件：${outputPath}`);
        
        // 显示前几条记录作为示例
        console.log('\n前3条转换后的记录示例：');
        const sampleIds = Object.keys(convertedData).slice(0, 3);
        sampleIds.forEach(id => {
            console.log(`记录 ${id}:`, JSON.stringify(convertedData[id], null, 2));
        });
        
    } catch (error) {
        console.error('转换过程中发生错误:', error.message);
        process.exit(1);
    }
}

// 运行脚本
if (require.main === module) {
    main();
}

// 导出函数供测试使用
module.exports = {
    readCSV,
    convertData
};