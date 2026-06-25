const fs = require('fs');
const html = fs.readFileSync('static/live.html', 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (m) {
  try {
    new Function(m[1]);
    console.log('JS OK');
  } catch(e) {
    console.log('Error:', e.message);
    // Find the problematic line
    const lines = m[1].split('\n');
    for (let i = 0; i < lines.length; i++) {
      try {
        new Function(lines.slice(0, i+1).join('\n'));
      } catch(e2) {
        console.log('First error at line', i+1, ':', lines[i].substring(0, 100));
        if (i > 0) console.log('Prev line', i, ':', lines[i-1].substring(0, 100));
        break;
      }
    }
  }
}
