// Optional owner-only local MP3 audition bridge.
// This is a temporary AUDIO PREVIEW, not an R2 import or publication approval.
// Visible automatically for the approved Clavier-Music track in /vi/; no upload to server.
(() => {
  const params = new URLSearchParams(location.search);
  if (location.pathname.replace(/\/+$/, "") !== "/vi") return;

  const expectedSha = "9756ade3d2f95a353cc82d5bd0cbad0ce450cada5bc6f1aca09192255e80254f";
  const expectedAssetRef = "r2-" + expectedSha;
  const panel = document.createElement("section");
  panel.className = "local-piano-audition";
  panel.id = "local-piano-audition";
  panel.style.cssText = "padding:12px;margin:12px 0;border:1px solid #79ab9d80;border-radius:8px;";
  const heading = document.createElement("strong");
  heading.textContent = "Piano cục bộ – nghe thử (không lưu R2)";
  const explanation = document.createElement("p");
  explanation.textContent = "Chọn file MP3 Clavier-Music đã tải về. Studio kiểm tra SHA-256 và gắn vào đúng track piano trong JSON; file ở trên máy, không tải lên máy chủ.";
  const picker = document.createElement("input");
  picker.type = "file";
  picker.accept = ".mp3,audio/mpeg";
  picker.setAttribute("aria-label", "Chọn file piano Clavier-Music MP3");
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.textContent = "Chưa chọn MP3. Chọn file Clavier-Music đã tải để mở khóa piano.";
  panel.append(heading, explanation, picker, status);
  const anchor = document.getElementById("timeline-scroll") ||
    document.getElementById("library-status");
  if (!anchor) return;
  anchor.insertAdjacentElement("beforebegin", panel);

  const projectUsesPiano = () => mix.tracks.some(track => {
    const asset = assets[track.asset];
    return asset?.id === expectedAssetRef;
  });
  const refreshVisibility = () => {
    panel.hidden = params.get("local-piano") !== "1" && !projectUsesPiano();
  };
  refreshVisibility();
  const timeline = document.getElementById("tracks");
  // A JSON import rebuilds the timeline. Reveal the picker automatically
  // when an approved piano placeholder appears, without requiring a URL flag.
  if (timeline && typeof MutationObserver !== "undefined") {
    new MutationObserver(refreshVisibility).observe(timeline, {childList:true});
  }

  let currentUrl = null;
  picker.addEventListener("change", async () => {
    const file = picker.files?.[0];
    if (!file) return;
    picker.disabled = true;
    status.textContent = "Đang kiểm tra SHA-256 và nguồn âm...";
    try {
      if (file.size < 4096 || file.size > 60_000_000 || !/\.mp3$/i.test(file.name)) {
        throw new Error("File phải là MP3 hợp lệ, nhỏ hơn 60 MB.");
      }
      const bytes = await file.arrayBuffer();
      const digest = await crypto.subtle.digest("SHA-256", bytes);
      const sha = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
      if (sha !== expectedSha) throw new Error("Sai bản MP3: mã SHA-256 không khớp với Clavier-Music đã duyệt.");
      const url = URL.createObjectURL(new Blob([bytes], {type:"audio/mpeg"}));
      let duration = 127.272;
      const audio = new Audio(url);
      audio.preload = "metadata";
      try {
        await new Promise((resolve, reject) => {
          audio.onloadedmetadata = resolve;
          audio.onerror = () => reject(new Error("Trình duyệt không đọc được metadata MP3"));
          audio.load();
        });
        if (!Number.isFinite(audio.duration) || audio.duration < 5 || audio.duration > 7200)
          throw new Error("Thời lượng MP3 không hợp lệ");
        duration = audio.duration;
      } catch (error) { URL.revokeObjectURL(url); throw error; }

      const index = rawAssetIndex.get(expectedAssetRef);
      const item = {
        id: expectedAssetRef,
        name:"Relaxing Piano Music – Clavier-Music (local preview)",
        aliases:"Clavier Music relaxing piano private owner local audition",
        key:"local-preview/" + sha + ".mp3",
        url,
        duration,
        group:"music",
        license:"Pixabay Content License",
        source:"https://pixabay.com/music/modern-classical-relaxing-piano-music-248868/",
        localAudition:true,
        assetStatus:"LOCAL_BROWSER_ONLY_NOT_R2_NOT_PUBLICATION_APPROVED"
      };
      let registeredIndex;
      if (Number.isInteger(index) && assets[index]?.pending===true &&
          assets[index]?.id===expectedAssetRef) {
        assets[index] = item;
        registeredIndex=index;
      } else if(Number.isInteger(index) && assets[index]?.localAudition===true) {
        if(currentUrl) URL.revokeObjectURL(currentUrl);
        assets[index] = item;
        registeredIndex=index;
      } else if(index === undefined) {
        registeredIndex=assets.length;
        rawAssetIndex.set(expectedAssetRef,registeredIndex);
        assets.push(item);
      } else {
        URL.revokeObjectURL(url);
        throw new Error("Trùng định danh với một nguồn đã đăng ký; không ghi đè.");
      }
      currentUrl = url;
      if (typeof stop === "function") stop();
      if (typeof rebuildCatalog === "function") rebuildCatalog();
      if (typeof refreshLibraryGroups === "function") refreshLibraryGroups();
      if (typeof renderLibrary === "function") renderLibrary();
      if (typeof render === "function") render();
      const included = mix.tracks.some(track => track.asset===registeredIndex);
      if(!included && typeof addSource==="function") addSource(registeredIndex);
      status.textContent = "Đã nạp MP3 Clavier-Music cục bộ. Bấm Phát để kiểm tra piano cùng tiếng mưa. File chưa được lưu R2.";
    } catch (error) {
      status.textContent = "Không thể nạp piano: "+String(error?.message || error);
    } finally { picker.disabled=false; }
  });
})();
