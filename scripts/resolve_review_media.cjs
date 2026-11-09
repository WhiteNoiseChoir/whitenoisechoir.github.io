"use strict";
const path = require("node:path");
const fs = require("node:fs");
const doc = JSON.parse(fs.readFileSync(path.join(__dirname,"../audio/review-media-dedup.json"),"utf8"));
const mappings = new Map(doc.pairs.map(p=>[p.review_path,p.production_path]));
function resolveReviewMedia(p) {
  const value = String(p).replace(/\\/g,"/").replace(/^\.\//,"");
  return mappings.get(value) || value;
}
module.exports = resolveReviewMedia;
