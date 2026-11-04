const fs = require('fs');

function countObjects(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const tickerMatches = content.match(/"ticker":/g) || [];
  const codeMatches = content.match(/"Code":/g) || [];
  return tickerMatches.length + codeMatches.length;
}

const rawCount = countObjects('backend/app/adapters/mock_adapter.py');
const indianCount = countObjects('backend/app/adapters/indian_stocks_fixtures.py');
const globalCount = countObjects('backend/app/adapters/global_stocks_fixtures.py');
const expandedCount = countObjects('backend/app/adapters/expanded_universe_fixtures.py');
const expandedIndianCount = countObjects('backend/app/adapters/expanded_indian_stocks_fixtures.py');

console.log('RAW_MOCK_SECURITIES:           ', rawCount);
console.log('INDIAN_MOCK_SECURITIES:        ', indianCount);
console.log('GLOBAL_MOCK_SECURITIES:        ', globalCount);
console.log('EXPANDED_MOCK_SECURITIES:      ', expandedCount);
console.log('EXPANDED_INDIAN_MOCK_SECURITIES:', expandedIndianCount);
console.log('-------------------------------------------');
const total = rawCount + indianCount + globalCount + expandedCount + expandedIndianCount;
console.log('TOTAL MOCK UNIVERSE COUNT:     ', total);
