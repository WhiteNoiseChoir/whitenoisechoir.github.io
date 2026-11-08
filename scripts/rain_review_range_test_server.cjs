#!/usr/bin/env node
"use strict";
/* Local GitHub Pages-style static HTTP server, including MP3 byte ranges.
 * Used only in CI to reproduce seek(595s) without downloading all 14MB first.
 */
const http=require("node:http"),fs=require("node:fs"),path=require("node:path");
const root=process.cwd(),port=8787;
const mime={".html":"text/html; charset=utf-8",".js":"application/javascript; charset=utf-8",".cjs":"text/plain; charset=utf-8",".mp3":"audio/mpeg",".m3u8":"application/vnd.apple.mpegurl",".ts":"video/mp2t",".json":"application/json; charset=utf-8",".css":"text/css; charset=utf-8",".xml":"application/xml; charset=utf-8"};
http.createServer((req,res)=>{
 try{
  if(req.method!=="GET"&&req.method!=="HEAD"){res.writeHead(405);return res.end();}
  const pathname=decodeURIComponent(new URL(req.url,"http://localhost").pathname);
  let file=path.resolve(root,"."+pathname);
  if(file!==root&&!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
  if(fs.existsSync(file)&&fs.statSync(file).isDirectory())file=path.join(file,"index.html");
  if(!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end("Not found");}
  const size=fs.statSync(file).size;
  const headers={"Accept-Ranges":"bytes","Content-Type":mime[path.extname(file)]||"application/octet-stream","Cache-Control":"no-store"};
  const range=req.headers.range;
  let start=0,end=size-1,status=200;
  if(range){
   const m=/^bytes=(\d+)-(\d*)$/.exec(range);
   if(!m){res.writeHead(416,{"Content-Range":"bytes */"+size});return res.end();}
   start=Number(m[1]);end=m[2]?Math.min(size-1,Number(m[2])):size-1;
   if(start>=size||end<start){res.writeHead(416,{"Content-Range":"bytes */"+size});return res.end();}
   status=206;
   headers["Content-Range"]="bytes "+start+"-"+end+"/"+size;
  }
  headers["Content-Length"]=end-start+1;
  res.writeHead(status,headers);
  if(req.method==="HEAD")return res.end();
  fs.createReadStream(file,{start,end}).on("error",()=>res.destroy()).pipe(res);
 }catch(e){res.writeHead(400);res.end("Bad request");}
}).listen(port,"127.0.0.1",()=>console.log("RAIN_REVIEW_TEST_SERVER_WITH_BYTE_RANGE_READY",port));
