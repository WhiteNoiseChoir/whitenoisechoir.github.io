#!/usr/bin/env node
"use strict";
/* C6B original-source triage: READ-ONLY. Never modifies an audio file, a
   release approval, an R2 object, a webpage or any catalog gate. */
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const cp=require("node:child_process");
const queue=JSON.parse(fs.readFileSync("catalog/sound-production-queue-c6.json","utf8"));
const value=(k)=>{const a=process.argv.find(x=>x.startsWith(k+"="));return a?a.slice(k.length+1):null};
const id=value("--id"),input=value("--file");
if(!id||!input)throw Error("Usage: node scripts/c6b_source_probe.cjs --id=SND-0039 --file=/absolute/path/to/original.wav");
const row=queue.items.find(x=>x.record_id===id);
if(!row)throw Error("Not in ten-item C6B P0 queue: "+id);
const file=path.resolve(input);
const stat=fs.statSync(file);
if(!stat.isFile()||stat.size<10000)throw Error("Not a valid nonempty source file");
const ffprobe=JSON.parse(cp.execFileSync("ffprobe",[
 "-v","error","-show_entries","format=duration,size,bit_rate,format_name:stream=codec_name,codec_type,sample_rate,channels,bits_per_raw_sample",
 "-of","json",file
],{encoding:"utf8",timeout:90000,maxBuffer:4e6}));
const audio=ffprobe.streams?.find(x=>x.codec_type==="audio");
if(!audio)throw Error("No decodable audio stream");
const duration=Number(ffprobe.format?.duration);
if(!Number.isFinite(duration)||duration<0)throw Error("Invalid duration");
const digest=crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const decode=cp.spawnSync("ffmpeg",["-hide_banner","-nostdin","-v","error","-xerror","-i",file,"-map","0:a:0","-f","null","-"],{encoding:"utf8",timeout:180000,maxBuffer:4e6});
const report={
 revision:"2026-11-10-C6B-SOURCE-TRIAGE",record_id:id,title_en:row.title_en,
 original_filename:path.basename(file),source_bytes:stat.size,original_sha256:digest,
 duration_seconds:duration,duration_container_ge_600:duration>=600,
 stream:audio,format_name:ffprobe.format?.format_name,container_bitrate:ffprobe.format?.bit_rate||null,
 whole_file_decode_status:decode.status===0&&!decode.error?"PASS":"FAIL",
 decode_error:(decode.stderr||"").slice(-2000),
 source_rights_status:"NOT_VERIFIED_BY_LOCAL_AUDIO_PROBE",
 independent_recording_status:"NOT_PROVABLE_FROM_CONTAINER_DURATION",
 speech_music_and_intrusive_events:"LISTENING_AUDIT_REQUIRED",
 similarity_against_existing_35:"A_B_AND_FINGERPRINT_AUDIT_REQUIRED",
 owner_listening:"NOT_APPROVED",
 release_authorized:false,
 can_enter_review_room:false
};
process.stdout.write(JSON.stringify(report,null,2)+"\n");
if(!report.duration_container_ge_600||report.whole_file_decode_status!=="PASS")process.exitCode=2;
