const youtubedl = require('youtube-dl-exec')
console.log("Starting yt-dlp test...")
youtubedl('https://www.youtube.com/watch?v=MMV94bm_Vpc', {
  dumpSingleJson: true,
  noCheckCertificates: true,
  noWarnings: true,
}).then(output => {
  console.log("Title: ", output.title)
  // output is the raw JSON from yt-dlp
  const formats = output.formats;
  console.log("Found formats count: ", formats.length)
  const f18 = formats.find(f => f.format_id === '18')
  console.log("Format 18 (360p) url: ", f18 ? "Yes" : "No")
  const f140 = formats.find(f => f.format_id === '140')
  console.log("Format 140 (m4a) url: ", f140 ? "Yes" : "No")
}).catch(err => {
    console.error("yt-dlp error:", err.message)
});
