// Run in the built-in browser (javascript_tool) on any episode page of a TikTok short drama,
// https://www.tiktok.com/shortdrama/episode/<dramaID>/<n>, with scripts/receive.py running.
// Set FIRST, LAST and NAME (the movie folder name) below.
//
// TikTok ties each video link to the browser's own session (curl gets 403), and the page's
// security policy blocks fetch/XHR to other hosts, but not a plain form POST. So the page reads
// its own episode list, fetches each episode's best video, puts the files (plus manifest.json:
// every episode's duration and subtitle links) into a multipart form and submits it to the
// receiver, which saves them and redirects back here. About 15 MB per episode: keep a batch to
// about 20 episodes, then run it again with the next range once receive.py prints "saved".
// The call returns at once; the upload happens a few seconds later and reloads the page.
const FIRST = 1, LAST = 20, NAME = 'Movie_Title';
window.__batch = async (first, last, name) => {
  const api = performance.getEntriesByType('resource').map(e => e.name).find(n => n.includes('/api/drama/episode/item_list/'));
  if (!api) throw new Error('episode list not loaded yet: wait and run again');
  let items = [], url = api;
  for (let p = 0; p < 20; p++) {
    const j = await (await fetch(url, { credentials: 'include' })).json();
    items = items.concat(j.itemList || []);
    if (!j.hasMore) break;
    url = api.replace(/([?&]cursor=)\d+/, `$1${j.cursor}`);
  }
  const best = it => [...it.video.bitrateInfo].sort((a, b) => (b.PlayAddr.Height - a.PlayAddr.Height) || (b.Bitrate - a.Bitrate))[0];
  const width = items.length > 99 ? 3 : 2;
  const manifest = items.map((it, i) => ({ ep: i + 1, id: it.id, desc: it.desc, duration: it.video.duration,
    quality: `${best(it).PlayAddr.Width}x${best(it).PlayAddr.Height} ${best(it).CodecType}`,
    subs: (it.video.subtitleInfos || []).map(s => ({ lang: s.LanguageCodeName, source: s.Source, url: s.Url })) }));
  const dt = new DataTransfer();
  dt.items.add(new File([JSON.stringify(manifest)], 'manifest.json'));
  for (let n = first; n <= Math.min(last, items.length); n++) {
    for (const u of best(items[n - 1]).PlayAddr.UrlList) {
      try {
        const r = await fetch(u, { credentials: 'include' });
        if (!r.ok) continue;
        dt.items.add(new File([await r.blob()], `${name}_Episode_${String(n).padStart(width, '0')}.mp4`));
        break;
      } catch (e) { /* try the next mirror */ }
    }
  }
  const form = document.createElement('form');
  form.method = 'POST'; form.enctype = 'multipart/form-data'; form.action = 'http://127.0.0.1:8765/upload';
  const back = document.createElement('input'); back.type = 'hidden'; back.name = 'back'; back.value = location.href;
  const files = document.createElement('input'); files.type = 'file'; files.name = 'f'; files.multiple = true; files.files = dt.files;
  form.append(back, files); document.body.appendChild(form); form.submit();
};
setTimeout(() => window.__batch(FIRST, LAST, NAME), 3000);
`fetching ${FIRST}-${LAST}`
