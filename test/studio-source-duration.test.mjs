import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const engine = readFileSync(new URL('../studio-engine.js', import.meta.url), 'utf8');
const ui = readFileSync(new URL('../studio-ui.js', import.meta.url), 'utf8');
const from = engine.indexOf('const decodedSourceDurations = new Map();');
const to = engine.indexOf("const sourceDiagnostics = document.createElement('details');");
const clipFrom = engine.indexOf('function clipOffset(track,sourceDuration){');
const clipTo = engine.indexOf('function scheduleTrack(engine,buffer,track,from,to,base,projectLength,destination=engine.destination){');
assert.ok(from >= 0 && to > from && clipFrom >= 0 && clipTo > clipFrom);
const helpers = engine.slice(clipFrom, clipTo) + '\n' + engine.slice(from, to);
function setup(assets, length = 600) {
  return vm.runInNewContext(helpers + '\n({studioSourceSeconds,studioEarlyEnd,decodedSourceDurations,clipDuration})',
    {assets, mix:{length}, Math, Number, Infinity});
}
const source = {duration:600, studioLoopKey:'asset-library/studio-loop/test.mp3', studioLoopSeconds:92};

test('a 600-second clip backed by a 92-second proxy warns when loop is disabled', () => {
  const {studioSourceSeconds,studioEarlyEnd,clipDuration} = setup([source]);
  const track = {asset:0,start:0,duration:600,offset:0,loop:false,gain:0.33};
  assert.equal(studioSourceSeconds(0),92);
  const issue = studioEarlyEnd(track);
  assert.equal(issue.source,92);
  assert.equal(issue.actual,92);
  assert.equal(issue.endAt,92);
  assert.equal(clipDuration(track,studioSourceSeconds(0),600),92);
});

test('loop mode preserves 600 seconds and removes the early-end warning', () => {
  const {studioSourceSeconds,studioEarlyEnd,clipDuration} = setup([source]);
  const track = {asset:0,start:0,duration:600,offset:0,loop:true,gain:0.33};
  assert.equal(studioEarlyEnd(track),null);
  assert.equal(clipDuration(track,studioSourceSeconds(0),600),600);
});

test('source offset consumes usable duration when loop is disabled', () => {
  const {studioEarlyEnd} = setup([source]);
  const issue=studioEarlyEnd({asset:0,start:10,duration:300,offset:32,loop:false});
  assert.equal(issue.actual,60);
  assert.equal(issue.endAt,70);
});

test('short events that fit in the source do not warn', () => {
  const {studioEarlyEnd}=setup([{duration:20}]);
  assert.equal(studioEarlyEnd({asset:0,start:100,duration:12,loop:false}),null);
});

test('browser decoded duration takes precedence over proxy metadata', () => {
  const {studioSourceSeconds,studioEarlyEnd,decodedSourceDurations}=setup([source]);
  decodedSourceDurations.set(0,87.5);
  assert.equal(studioSourceSeconds(0),87.5);
  assert.equal(studioEarlyEnd({asset:0,start:0,duration:600,loop:false}).actual,87.5);
});

test('UI reflects source duration and offers the owner a loop fix', () => {
  assert.match(ui,/clipDuration\(\{\.\.\.track, start: time\}, studioSourceSeconds\(track.asset\)/);
  assert.match(ui,/Bật Lặp cho lớp này/);
  assert.match(ui,/studioEarlyEnd\(track\)/);
});

test('WAV export still snapshots the currently edited mix', () => {
  assert.match(engine,/const project=restrictHomeMix\(structuredClone\(mix\)\)/);
  assert.match(engine,/await buildWav\(project,/);
  assert.match(engine,/audioSignature\(project\)/);
});
