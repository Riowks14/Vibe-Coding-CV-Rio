from base64 import b64encode
import hashlib
import hmac
from io import BytesIO
import os
import secrets
import uuid
import warnings
import webbrowser

from flask import Flask, jsonify, render_template_string, request
from PIL import Image, ImageOps, UnidentifiedImageError
import psycopg
from psycopg.types.json import Jsonb
from werkzeug.exceptions import RequestEntityTooLarge

MAX_PHOTO_BYTES = 2 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_PHOTO_BYTES + 64 * 1024
MAX_PHOTO_PIXELS = 25_000_000
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
HTML_PAGE = r"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f7f8fc">
  <title>BuildCV - CV Builder</title>
  <style>
    :root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#172033;background:#f6f7fb}
    *{box-sizing:border-box}body{margin:0}button,input,textarea,select{font:inherit}button{cursor:pointer}
    .topbar{height:72px;background:#fff;border-bottom:1px solid #e8eaf1;display:flex;align-items:center;justify-content:space-between;padding:0 24px;position:sticky;top:0;z-index:10}
    .brand{font-weight:800;font-size:22px;letter-spacing:-.6px}.brand b{color:#6658e8}
    .actions{display:flex;gap:10px;align-items:center}
    .button{border:1px solid #e1e4ed;background:#fff;color:#414a5d;border-radius:10px;padding:10px 16px;font-weight:700}
    .button.primary{background:#6658e8;border-color:#6658e8;color:#fff}
    .page{max-width:1280px;margin:0 auto;padding:34px 24px 72px}
    .eyebrow{color:#6559d9;font-size:12px;font-weight:800;letter-spacing:1.3px;text-transform:uppercase}
    h1{font-size:clamp(28px,4vw,40px);letter-spacing:-1.3px;margin:8px 0}.lede{color:#6c7486;max-width:700px;line-height:1.65;margin:0}
    .steps{display:flex;gap:9px;flex-wrap:wrap;margin:28px 0}.step{border:1px solid #e2e5ee;background:#fff;border-radius:99px;padding:9px 15px;font-size:13px;color:#6c7486}.step.active{color:#4f45c7;border-color:#c9c4ff;background:#f0efff;font-weight:700}
    .toolbar{display:flex;justify-content:space-between;align-items:center;gap:14px;margin:28px 0 18px;flex-wrap:wrap}.tabs{display:flex;gap:8px}.tab{border:1px solid #e1e4ed;background:#fff;color:#414a5d;border-radius:10px;padding:10px 15px;font-weight:700}.tab.selected{background:#252d49;color:#fff;border-color:#252d49}
    .template-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.template-card{background:#fff;border:1px solid #e5e7ef;border-radius:16px;overflow:hidden;display:flex;flex-direction:column}.template-card.chosen{border:2px solid #6a5de8;box-shadow:0 8px 28px rgba(102,88,232,0.15)}
    .mini{height:190px;background:#f0f2f8;padding:17px 22px;display:flex;justify-content:center;overflow:hidden}.mini-paper{width:120px;height:160px;background:#fff;box-shadow:0 3px 12px rgba(29,37,68,0.12);padding:13px 11px;display:flex;gap:7px;color:#172033}.mini-side{width:34px;background:#34415e;margin:-13px 0 -13px -11px;padding:11px 5px;display:flex;flex-direction:column;gap:5px}.mini-line{height:3px;background:#d8dce7;border-radius:3px}.mini-title{height:6px;width:54%;background:#313b59;border-radius:4px;margin-bottom:2px}.mini-head{height:16px;background:#edf0f7;margin:-2px -2px 3px}.mini-dot{width:13px;height:13px;border-radius:50%;background:#cdd3e0;margin:0 auto 2px}.mini-accent{height:5px;width:60%;background:#7664e8;border-radius:4px;margin:2px 0}.mini-lines{display:flex;flex-direction:column;gap:5px;flex:1}.mini-line.short{width:55%}.mini-line.mid{width:76%}
    .card-body{padding:17px 18px 18px;display:flex;flex-direction:column;flex:1}.card-kicker{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#7064d6;font-weight:800}.card-body h3{margin:6px 0;font-size:17px}.card-body p{font-size:13px;line-height:1.55;color:#70788a;margin:0 0 16px;flex:1}.card-foot{display:flex;align-items:center;justify-content:space-between;gap:8px}.badge{font-size:10px;padding:5px 8px;border-radius:99px;background:#f0efff;color:#584cca;font-weight:700}
    .builder{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(440px,1.2fr);gap:20px;align-items:start}.panel{background:#fff;border:1px solid #e6e8f0;border-radius:16px;padding:20px}.panel h2{font-size:18px;margin:0 0 5px}.panel-sub{font-size:12px;color:#7a8291;margin:0 0 18px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{display:flex;flex-direction:column;gap:6px}.field.full{grid-column:1/-1}.field label{font-size:12px;font-weight:700;color:#454e62}.field input,.field textarea{border:1px solid #e0e3ec;border-radius:8px;padding:10px 11px;outline:none;width:100%;background:#fff}.field textarea{resize:vertical;min-height:84px}.field input:focus,.field textarea:focus{border-color:#8176e9;box-shadow:0 0 0 3px rgba(117,103,232,0.14)}
    .section-head{display:flex;align-items:center;justify-content:space-between;margin:22px 0 10px}.section-head h3{font-size:14px;margin:0}.entry{border:1px solid #edf0f5;border-radius:10px;padding:12px;margin:9px 0}.entry-remove{border:0;background:none;color:#9b5260;font-size:12px;padding:4px}.add-button{border:1px dashed #c9cde0;background:#fafaff;color:#554aca;border-radius:8px;padding:9px 12px;font-weight:700;font-size:12px;width:100%}
    .preview-panel{position:sticky;top:88px}.preview-tools{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.paper-wrap{background:#eef0f5;padding:20px;border-radius:12px;max-height:calc(100vh - 200px);overflow:auto}.resume{width:100%;max-width:595px;min-height:842px;margin:0 auto;background:#fff;color:#1d2638;box-shadow:0 5px 24px rgba(27,36,64,0.12);padding:42px 45px;font-family:Arial,sans-serif;font-size:11px;line-height:1.48;overflow-wrap:anywhere}.resume h1{font-size:27px;letter-spacing:-0.7px;margin:0 0 4px;color:#202a40}.resume .contact{font-size:9px;color:#637087;margin:0 0 18px}.resume .contact-list{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}.resume .contact-item{display:inline-flex;align-items:center;white-space:nowrap}.resume .contact-item + .contact-item::before{content:"|";margin-right:8px;color:#8a93a7}.resume h2{font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:#394768;margin:17px 0 7px;border-bottom:1px solid #dce1eb;padding-bottom:4px}.resume p{margin:4px 0}.resume .resume-entry{margin:8px 0}.resume .resume-entry strong{font-size:11px}.resume .muted{color:#697487}.resume .resume-head{margin-bottom:12px}.resume .resume-columns{display:grid;grid-template-columns:1fr 1fr;gap:21px}
    .builder.readonly{grid-template-columns:1fr}.builder.readonly .preview-panel{position:static}
    .purpose-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 16px;background:#fff;border:1px solid #e8eaf1;border-radius:14px;margin:0 0 20px}
    .purpose-row label{font-size:13px;font-weight:700}.purpose-row select{border:1px solid #dfe2eb;background:#fff;border-radius:8px;padding:9px 32px 9px 11px;color:#273149}
    .purpose-note{font-size:12px;color:#7a8292}
    dialog{width:min(460px,calc(100% - 32px));border:1px solid #e6e8f0;border-radius:16px;padding:24px;color:#172033}
    dialog::backdrop{background:rgba(23,32,51,.45)}
    dialog h2{margin-top:0}dialog p{color:#6c7486;line-height:1.5}
    dialog label{display:block;font-size:13px;font-weight:700;margin:14px 0 6px}
    dialog input{width:100%;border:1px solid #dfe2eb;border-radius:8px;padding:10px;margin-bottom:8px}
    .hidden{display:none !important}
    @media (max-width:980px){.builder{grid-template-columns:1fr}.preview-panel{position:relative;top:0}.template-grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">Build<b>CV</b></div>
    <div class="actions">
      <button class="button primary" id="save-cv">Simpan &amp; buat link</button>
      <button class="button hidden" id="edit-cv">Edit CV</button>
      <button class="button" id="change-design">Ubah desain</button>
      <button class="button primary" id="download-pdf">Unduh PDF</button>
    </div>
  </header>
  <main class="page">
    <div class="eyebrow">Curriculum Vitae Builder</div>
    <h1>Bangun CV profesional dalam hitungan menit.</h1>
    <p class="lede">Pilih template, isi data diri, dan hasilkan CV siap cetak dalam desain yang rapi dan modern.</p>

    <div class="steps">
      <div class="step active">1. Pilih template</div>
      <div class="step">2. Isi data</div>
      <div class="step">3. Preview & unduh</div>
    </div>

    <div class="toolbar">
      <div class="tabs">
        <button class="tab selected" data-category="all">Semua</button>
        <button class="tab" data-category="modern">Modern</button>
        <button class="tab" data-category="classic">Classic</button>
        <button class="tab" data-category="ultra">Ultra</button>
      </div>
    </div>

    <div id="template-grid" class="template-grid"></div>

    <section id="builder" class="builder hidden">
      <div class="panel" id="input-panel">
        <h2>Informasi CV</h2>
        <p class="panel-sub">Lengkapi kolom di bawah ini untuk memperbarui preview.</p>
        <div id="form-fields"></div>
      </div>
      <div class="panel preview-panel">
        <div class="preview-tools">
          <div><strong id="preview-name">CV Anda</strong></div>
          <div class="badge" id="preview-purpose">Tujuan</div>
        </div>
        <div class="paper-wrap"><div id="resume" class="resume"></div></div>
      </div>
    </section>
  </main>

  <dialog id="share-dialog">
    <form method="dialog">
      <h2>CV berhasil disimpan</h2>
      <p>Simpan link publik dan kode edit ini secara terpisah. Siapa pun yang memiliki kode dapat mengubah CV.</p>
      <label for="share-url">Link untuk melihat CV</label>
      <input id="share-url" readonly>
      <label for="share-edit-code">Kode rahasia untuk mengedit</label>
      <input id="share-edit-code" readonly>
      <button class="button primary">Selesai</button>
    </form>
  </dialog>
  <dialog id="edit-dialog">
    <form id="edit-form">
      <h2>Edit CV</h2>
      <p>Masukkan kode rahasia pemilik untuk mengubah CV ini.</p>
      <label for="edit-code">Kode edit</label>
      <input id="edit-code" type="password" autocomplete="current-password" required>
      <p id="edit-error" role="alert"></p>
      <div class="actions">
        <button class="button" type="button" id="cancel-edit">Batal</button>
        <button class="button primary" type="submit">Buka akses edit</button>
      </div>
    </form>
  </dialog>

  <script>
    const STORAGE_KEY = 'buildcv-state-v1';
    const INITIAL_CV_ID = {{ cv_id|tojson }};
    const defaultState = {
      purpose: 'job',
      template: 'classic',
      name: 'Rio Wibawa',
      title: 'Full-Stack Developer',
      email: 'rio@email.com',
      phone: '+62 812 3456 7890',
      location: 'Jakarta, Indonesia',
      website: 'www.rio.dev',
      summary: 'Saya adalah developer yang fokus pada product engineering, pengembangan aplikasi web, dan pengalaman pengguna yang rapi dan efisien.',
      skills: ['HTML', 'CSS', 'JavaScript', 'React', 'Node.js', 'Python', 'UI/UX'],
      experience: [
        { role: 'Senior Frontend Developer', company: 'PT. Digital Nusantara', period: '2022 - Sekarang', description: 'Membangun dashboard produk, optimasi performa frontend, dan design system untuk tim produk.' },
        { role: 'Frontend Developer', company: 'Startup E-Commerce', period: '2020 - 2022', description: 'Mengembangkan fitur e-commerce, integrasi API, serta pengalaman checkout yang lebih ringan dan cepat.' }
      ],
      education: [
        { degree: 'S1 Teknik Informatika', school: 'Universitas Indonesia', period: '2016 - 2020' }
      ],
      projects: [
        { name: 'BuildCV', description: 'Aplikasi builder CV berbasis web untuk menghasilkan dokumen CV yang menarik dan siap cetak.' }
      ],
      social: { linkedin: 'linkedin.com/in/rio', github: 'github.com/rio' }
    };

    const purposes = { job: { label: 'Lamaran kerja' }, internship: { label: 'Magang' }, freelance: { label: 'Freelance' }, scholarship: { label: 'Beasiswa' } };
    const templates = [
      { id: 'classic', category: 'classic', name: 'Classic', desc: 'Formal dan profesional untuk lamaran kerja.', badge: 'Classic' },
      { id: 'ats', category: 'modern', name: 'ATS', desc: 'Tata letak sederhana dan mudah dibaca.', badge: 'Modern' },
      { id: 'editorial', category: 'ultra', name: 'Editorial', desc: 'Desain premium dan elegan.', badge: 'Ultra' },
      { id: 'profile', category: 'modern', name: 'Profile', desc: 'Fokus pada identitas dan portofolio.', badge: 'Modern' },
      { id: 'timeline', category: 'ultra', name: 'Timeline', desc: 'Rincian pengalaman dengan alur kronologis.', badge: 'Ultra' },
      { id: 'portfolio', category: 'modern', name: 'Portfolio', desc: 'Cocok untuk kandidat kreatif dan developer.', badge: 'Modern' }
    ];
    let category = 'all';
    let state = loadState();
    let activeCvId = INITIAL_CV_ID;
    let editKey = null;
    let canEdit = !activeCvId;

    function editKeyStorageKey(cvId) {
      return `buildcv-edit-key-${cvId}`;
    }

    function loadState() {
      try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        return { ...defaultState, ...saved };
      } catch { return { ...defaultState }; }
    }

    function save() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }

    function escapeHtml(value = '') {
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function renderPurposes() {
      const choose = document.getElementById('purpose');
      if (!choose) {
        const wrapper = document.createElement('div');
        wrapper.className = 'purpose-row';
        wrapper.innerHTML = '<label for="purpose">Tujuan CV</label><select id="purpose">' + Object.entries(purposes).map(([key, value]) => '<option value="' + key + '" ' + (state.purpose === key ? 'selected' : '') + '>' + value.label + '</option>').join('') + '</select><span class="purpose-note">Pilih sesuai kebutuhan lamaran Anda.</span>';
        document.querySelector('.page').insertBefore(wrapper, document.getElementById('template-grid'));
      } else {
        choose.value = state.purpose;
      }
    }

    function renderTemplates() {
      const grid = document.getElementById('template-grid');
      if (!grid) return;
      grid.innerHTML = templates
        .filter(item => category === 'all' || item.category === category)
        .map(item => `
          <div class="template-card ${state.template === item.id ? 'chosen' : ''}" data-template="${item.id}">
            <div class="mini">
              <div class="mini-paper">
                <div class="mini-side">
                  <div class="mini-dot"></div>
                  <div class="mini-line"></div>
                  <div class="mini-line"></div>
                  <div class="mini-line"></div>
                  <div class="mini-accent"></div>
                </div>
                <div class="mini-lines">
                  <div class="mini-title"></div>
                  <div class="mini-line mid"></div>
                  <div class="mini-line short"></div>
                  <div class="mini-head"></div>
                  <div class="mini-line"></div>
                  <div class="mini-line"></div>
                  <div class="mini-line short"></div>
                </div>
              </div>
            </div>
            <div class="card-body">
              <div class="card-kicker">Template</div>
              <h3>${item.name}</h3>
              <p>${item.desc}</p>
              <div class="card-foot">
                <span class="badge">${item.badge}</span>
                <button class="button primary" data-template="${item.id}">Pilih</button>
              </div>
            </div>
          </div>
        `).join('');
    }

    function renderForm() {
      const form = document.getElementById('form-fields');
      form.innerHTML = `
        <div class="field-grid">
          <div class="field"><label>Nama lengkap</label><input id="name" value="${escapeHtml(state.name)}"></div>
          <div class="field"><label>Judul</label><input id="title" value="${escapeHtml(state.title)}"></div>
          <div class="field"><label>Email</label><input id="email" value="${escapeHtml(state.email)}"></div>
          <div class="field"><label>Telepon</label><input id="phone" value="${escapeHtml(state.phone)}"></div>
          <div class="field"><label>Lokasi</label><input id="location" value="${escapeHtml(state.location)}"></div>
          <div class="field"><label>Website</label><input id="website" value="${escapeHtml(state.website)}"></div>
          <div class="field full"><label>Ringkasan profil</label><textarea id="summary">${escapeHtml(state.summary)}</textarea></div>
          <div class="field full"><label>Keahlian</label><input id="skills" value="${escapeHtml((state.skills || []).join(', '))}"></div>
          <div class="field full"><label>LinkedIn</label><input id="linkedin" value="${escapeHtml(state.social?.linkedin || '')}"></div>
          <div class="field full"><label>GitHub</label><input id="github" value="${escapeHtml(state.social?.github || '')}"></div>
        </div>
        <div class="section-head"><h3>Pengalaman Kerja</h3><button class="button" data-add="experience">+ Tambah</button></div>
        <div id="experience-list">${(state.experience || []).map((exp, idx) => `<div class="entry"><div class="field-grid"><div class="field"><label>Jabatan</label><input data-field="experience" data-index="${idx}" data-key="role" value="${escapeHtml(exp.role || '')}"></div><div class="field"><label>Perusahaan</label><input data-field="experience" data-index="${idx}" data-key="company" value="${escapeHtml(exp.company || '')}"></div><div class="field"><label>Periode</label><input data-field="experience" data-index="${idx}" data-key="period" value="${escapeHtml(exp.period || '')}"></div><div class="field full"><label>Deskripsi</label><textarea data-field="experience" data-index="${idx}" data-key="description">${escapeHtml(exp.description || '')}</textarea></div></div><button class="entry-remove" data-remove="experience:${idx}">Hapus</button></div>`).join('') || '<div class="entry">Belum ada pengalaman</div>'}</div>
        <div class="section-head"><h3>Pendidikan</h3><button class="button" data-add="education">+ Tambah</button></div>
        <div id="education-list">${(state.education || []).map((edu, idx) => `<div class="entry"><div class="field-grid"><div class="field"><label>Gelar</label><input data-field="education" data-index="${idx}" data-key="degree" value="${escapeHtml(edu.degree || '')}"></div><div class="field"><label>Sekolah</label><input data-field="education" data-index="${idx}" data-key="school" value="${escapeHtml(edu.school || '')}"></div><div class="field"><label>Periode</label><input data-field="education" data-index="${idx}" data-key="period" value="${escapeHtml(edu.period || '')}"></div></div><button class="entry-remove" data-remove="education:${idx}">Hapus</button></div>`).join('') || '<div class="entry">Belum ada pendidikan</div>'}</div>
        <div class="section-head"><h3>Proyek</h3><button class="button" data-add="projects">+ Tambah</button></div>
        <div id="projects-list">${(state.projects || []).map((proj, idx) => `<div class="entry"><div class="field-grid"><div class="field"><label>Nama proyek</label><input data-field="projects" data-index="${idx}" data-key="name" value="${escapeHtml(proj.name || '')}"></div><div class="field full"><label>Deskripsi</label><textarea data-field="projects" data-index="${idx}" data-key="description">${escapeHtml(proj.description || '')}</textarea></div></div><button class="entry-remove" data-remove="projects:${idx}">Hapus</button></div>`).join('') || '<div class="entry">Belum ada proyek</div>'}</div>
      `;
    }

    function renderPreview() {
      const resume = document.getElementById('resume');
      if (!resume) return;
      const skills = (state.skills || []).join(' \u2022 ');
      const experience = (state.experience || []).map(exp => `<div class="resume-entry"><strong>${escapeHtml(exp.role || '')}</strong><div>${escapeHtml(exp.company || '')} &middot; ${escapeHtml(exp.period || '')}</div><div class="muted">${escapeHtml(exp.description || '')}</div></div>`).join('');
      const education = (state.education || []).map(edu => `<div class="resume-entry"><strong>${escapeHtml(edu.degree || '')}</strong><div>${escapeHtml(edu.school || '')} &middot; ${escapeHtml(edu.period || '')}</div></div>`).join('');
      const projects = (state.projects || []).map(proj => `<div class="resume-entry"><strong>${escapeHtml(proj.name || '')}</strong><div class="muted">${escapeHtml(proj.description || '')}</div></div>`).join('');

      resume.innerHTML = `
        <div class="resume-head">
          <h1>${escapeHtml(state.name || 'Nama Anda')}</h1>
          <div class="muted">${escapeHtml(state.title || 'Judul profesional')}</div>
        </div>
        <div class="contact">
          <div class="contact-list">
            ${state.email ? '<span class="contact-item">' + escapeHtml(state.email) + '</span>' : ''}
            ${state.phone ? '<span class="contact-item">' + escapeHtml(state.phone) + '</span>' : ''}
            ${state.location ? '<span class="contact-item">' + escapeHtml(state.location) + '</span>' : ''}
            ${state.website ? '<span class="contact-item">' + escapeHtml(state.website) + '</span>' : ''}
            ${state.social?.linkedin ? '<span class="contact-item">' + escapeHtml(state.social.linkedin) + '</span>' : ''}
            ${state.social?.github ? '<span class="contact-item">' + escapeHtml(state.social.github) + '</span>' : ''}
          </div>
        </div>
        <div class="resume-columns">
          <div>
            <h2>Profil</h2>
            <p>${escapeHtml(state.summary || 'Ringkasan profil Anda...')}</p>
            <h2>Pengalaman</h2>
            ${experience || '<p>Belum ada pengalaman.</p>'}
            <h2>Pendidikan</h2>
            ${education || '<p>Belum ada pendidikan.</p>'}
          </div>
          <div>
            <h2>Keahlian</h2>
            <p>${escapeHtml(skills || 'Tambahkan keahlian Anda')}</p>
            <h2>Proyek</h2>
            ${projects || '<p>Belum ada proyek.</p>'}
          </div>
        </div>
      `;
      document.getElementById('preview-name').textContent = (state.name || 'CV Anda') + ' - ' + (purposes[state.purpose]?.label || 'Tujuan');
      document.getElementById('preview-purpose').textContent = purposes[state.purpose]?.label || 'Tujuan';
    }

    function syncFromInputs() {
      state.name = document.getElementById('name')?.value || state.name;
      state.title = document.getElementById('title')?.value || state.title;
      state.email = document.getElementById('email')?.value || state.email;
      state.phone = document.getElementById('phone')?.value || state.phone;
      state.location = document.getElementById('location')?.value || state.location;
      state.website = document.getElementById('website')?.value || state.website;
      state.summary = document.getElementById('summary')?.value || state.summary;
      state.skills = (document.getElementById('skills')?.value || '').split(',').map(item => item.trim()).filter(Boolean);
      state.social = { linkedin: document.getElementById('linkedin')?.value || '', github: document.getElementById('github')?.value || '' };
      save();
      renderPreview();
    }

    function bindEvents() {
      document.addEventListener('input', (event) => {
        const target = event.target;
        if (target.id && ['name','title','email','phone','location','website','summary','skills','linkedin','github'].includes(target.id)) {
          syncFromInputs();
        }
        if (target.dataset.field) {
          const section = target.dataset.field;
          const index = Number(target.dataset.index);
          const key = target.dataset.key;
          if (state[section] && state[section][index]) {
            state[section][index][key] = target.value;
            save();
            renderPreview();
          }
        }
      });

      document.addEventListener('click', (event) => {
        const templateButton = event.target.closest('[data-template]');
        if (templateButton) {
          state.template = templateButton.dataset.template;
          save();
          renderTemplates();
          renderPreview();
          document.getElementById('builder').classList.remove('hidden');
          document.getElementById('template-grid').classList.add('hidden');
          document.querySelector('.toolbar').classList.add('hidden');
          document.querySelector('.steps').classList.add('hidden');
          return;
        }
        const add = event.target.closest('[data-add]');
        if (add) {
          const section = add.dataset.add;
          if (!state[section]) state[section] = [];
          state[section].push({});
          save();
          renderForm();
          renderPreview();
          return;
        }
        const remove = event.target.closest('[data-remove]');
        if (remove) {
          const [section, index] = remove.dataset.remove.split(':');
          state[section].splice(Number(index), 1);
          save();
          renderForm();
          renderPreview();
          return;
        }
        if (event.target.id === 'change-design') {
          document.getElementById('builder').classList.add('hidden');
          document.getElementById('template-grid').classList.remove('hidden');
          document.querySelector('.toolbar').classList.remove('hidden');
          document.querySelector('.steps').classList.remove('hidden');
          renderTemplates();
          return;
        }
        if (event.target.id === 'download-pdf') {
          window.print();
        }
        if (event.target.id === 'save-cv') {
          saveCurrentCV();
        }
        if (event.target.id === 'edit-cv') {
          document.getElementById('edit-error').textContent = '';
          document.getElementById('edit-code').value = '';
          document.getElementById('edit-dialog').showModal();
        }
        if (event.target.id === 'cancel-edit') {
          document.getElementById('edit-dialog').close();
        }
      });

      document.addEventListener('change', (event) => {
        if (event.target.id === 'purpose') {
          state.purpose = event.target.value;
          save();
          renderPreview();
        }
      });

      document.getElementById('edit-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const key = document.getElementById('edit-code').value;
        try {
          await apiRequest(`/api/cvs/${activeCvId}/authorize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ edit_key: key })
          });
          editKey = key;
          canEdit = true;
          localStorage.setItem(editKeyStorageKey(activeCvId), key);
          setAccessMode();
          document.getElementById('edit-dialog').close();
        } catch (error) {
          document.getElementById('edit-error').textContent = error.message;
        }
      });

      document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
          category = tab.dataset.category;
          document.querySelectorAll('.tab').forEach(item => item.classList.toggle('selected', item === tab));
          renderTemplates();
        });
      });
    }

    async function apiRequest(url, options = {}) {
      const response = await fetch(url, options);
      const result = await response.json();
      if (!response.ok) {
        const error = new Error(result.error || 'Permintaan gagal. Coba lagi.');
        error.status = response.status;
        throw error;
      }
      return result;
    }

    function setAccessMode() {
      const inputPanel = document.getElementById('input-panel');
      inputPanel.classList.toggle('hidden', !canEdit);
      document.getElementById('builder').classList.toggle('readonly', !canEdit);
      document.getElementById('save-cv').classList.toggle('hidden', !canEdit);
      document.getElementById('save-cv').textContent = activeCvId ? 'Simpan perubahan' : 'Simpan & buat link';
      document.getElementById('edit-cv').classList.toggle('hidden', canEdit || !activeCvId);
      document.getElementById('change-design').classList.toggle('hidden', !canEdit);
    }

    async function saveCurrentCV() {
      const button = document.getElementById('save-cv');
      button.disabled = true;
      try {
        if (!activeCvId) {
          const result = await apiRequest('/api/cvs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state })
          });
          activeCvId = result.id;
          editKey = result.edit_key;
          let storageWarning = '';
          try {
            localStorage.setItem(editKeyStorageKey(activeCvId), editKey);
          } catch {
            storageWarning = 'Browser tidak dapat mengingat kode edit. Simpan kode yang ditampilkan agar CV tetap bisa diedit setelah halaman ditutup.';
          }
          history.replaceState(null, '', `/cv/${activeCvId}`);
          document.getElementById('share-url').value = `${location.origin}/cv/${activeCvId}`;
          document.getElementById('share-edit-code').value = editKey;
          document.getElementById('share-dialog').showModal();
          setAccessMode();
          if (storageWarning) alert(storageWarning);
        } else {
          await apiRequest(`/api/cvs/${activeCvId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'X-Edit-Key': editKey },
            body: JSON.stringify({ state })
          });
          alert('Perubahan CV berhasil disimpan.');
        }
      } catch (error) {
        alert(error.message);
      } finally {
        button.disabled = false;
      }
    }

    async function init() {
      renderPurposes();
      renderTemplates();
      bindEvents();
      document.getElementById('builder').classList.remove('hidden');
      document.getElementById('template-grid').classList.add('hidden');
      document.querySelector('.toolbar').classList.add('hidden');
      document.querySelector('.steps').id = 'steps';
      document.getElementById('steps').classList.add('hidden');
      setAccessMode();

      if (activeCvId) {
        try {
          const result = await apiRequest(`/api/cvs/${activeCvId}`);
          state = result.state;
          const savedKey = localStorage.getItem(editKeyStorageKey(activeCvId));
          if (savedKey) {
            try {
              await apiRequest(`/api/cvs/${activeCvId}/authorize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ edit_key: savedKey })
              });
              editKey = savedKey;
              canEdit = true;
            } catch (error) {
              if (error.status === 403) {
                localStorage.removeItem(editKeyStorageKey(activeCvId));
              } else {
                alert(error.message);
              }
            }
          }
        } catch (error) {
          document.getElementById('resume').textContent = error.message;
          return;
        }
      }

      renderForm();
      renderPreview();
      setAccessMode();
    }

    init();
  </script>
</body>
</html>
"""


@app.errorhandler(RequestEntityTooLarge)
def handle_oversized_request(_error):
    return jsonify(error="Ukuran unggahan melebihi batas maksimum 2 MB."), _error.code or 413


@app.get("/")
@app.get("/index.html")
def index():
    return render_template_string(HTML_PAGE, cv_id=None)


def database_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL belum dikonfigurasi.")
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url.removeprefix("postgres://")
    return psycopg.connect(database_url)


def ensure_cv_table(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cvs (
            id UUID PRIMARY KEY,
            state JSONB NOT NULL,
            edit_key_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


def valid_edit_key(connection, cv_id, edit_key):
    if not isinstance(edit_key, str) or not edit_key:
        return False
    row = connection.execute(
        "SELECT edit_key_hash FROM cvs WHERE id = %s",
        (cv_id,),
    ).fetchone()
    if row is None:
        return False
    provided_hash = hashlib.sha256(edit_key.encode("utf-8")).hexdigest()
    return hmac.compare_digest(row[0], provided_hash)


@app.get("/cv/<uuid:cv_id>")
def view_cv(cv_id):
    return render_template_string(HTML_PAGE, cv_id=str(cv_id))


@app.post("/api/cvs")
def create_cv():
    payload = request.get_json(silent=True)
    state = payload.get("state") if isinstance(payload, dict) else None
    if not isinstance(state, dict):
        return jsonify(error="Data CV tidak valid."), 400

    cv_id = uuid.uuid4()
    edit_key = secrets.token_urlsafe(32)
    edit_key_hash = hashlib.sha256(edit_key.encode("utf-8")).hexdigest()
    try:
        with database_connection() as connection:
            ensure_cv_table(connection)
            connection.execute(
                "INSERT INTO cvs (id, state, edit_key_hash) VALUES (%s, %s, %s)",
                (cv_id, Jsonb(state), edit_key_hash),
            )
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Gagal membuat CV di database.")
        return jsonify(error="Database tidak tersedia. Coba lagi nanti."), 503

    return jsonify(id=str(cv_id), edit_key=edit_key), 201


@app.get("/api/cvs/<uuid:cv_id>")
def get_cv(cv_id):
    try:
        with database_connection() as connection:
            ensure_cv_table(connection)
            row = connection.execute(
                "SELECT state FROM cvs WHERE id = %s",
                (cv_id,),
            ).fetchone()
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Gagal membaca CV dari database.")
        return jsonify(error="Database tidak tersedia. Coba lagi nanti."), 503

    if row is None:
        return jsonify(error="CV tidak ditemukan."), 404
    return jsonify(state=row[0])


@app.post("/api/cvs/<uuid:cv_id>/authorize")
def authorize_cv_edit(cv_id):
    payload = request.get_json(silent=True)
    edit_key = payload.get("edit_key") if isinstance(payload, dict) else None
    try:
        with database_connection() as connection:
            ensure_cv_table(connection)
            authorized = valid_edit_key(connection, cv_id, edit_key)
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Gagal memverifikasi akses edit CV.")
        return jsonify(error="Database tidak tersedia. Coba lagi nanti."), 503

    if not authorized:
        return jsonify(error="Kode edit salah atau CV tidak ditemukan."), 403
    return jsonify(authorized=True)


@app.put("/api/cvs/<uuid:cv_id>")
def update_cv(cv_id):
    payload = request.get_json(silent=True)
    state = payload.get("state") if isinstance(payload, dict) else None
    if not isinstance(state, dict):
        return jsonify(error="Data CV tidak valid."), 400

    edit_key = request.headers.get("X-Edit-Key", "")
    try:
        with database_connection() as connection:
            ensure_cv_table(connection)
            if not valid_edit_key(connection, cv_id, edit_key):
                return jsonify(error="Kode edit salah atau CV tidak ditemukan."), 403
            connection.execute(
                "UPDATE cvs SET state = %s, updated_at = NOW() WHERE id = %s",
                (Jsonb(state), cv_id),
            )
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Gagal menyimpan perubahan CV.")
        return jsonify(error="Database tidak tersedia. Coba lagi nanti."), 503
    return jsonify(saved=True)


@app.post("/api/profile-photo")
def upload_profile_photo():
    uploaded = request.files.get("photo")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Pilih foto JPG, JPEG, atau PNG terlebih dahulu."), 400

    extension = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
    if extension not in {"jpg", "jpeg", "png"}:
        return jsonify(error="Format tidak didukung. Pilih file JPG, JPEG, atau PNG."), 415

    content = uploaded.stream.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        return jsonify(error="Ukuran foto melebihi batas 2 MB. Pilih file yang lebih kecil."), 413
    if not content:
        return jsonify(error="File foto kosong. Pilih gambar lain."), 400

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                actual_format = image.format
                if actual_format not in {"JPEG", "PNG"}:
                    return jsonify(error="Isi file bukan gambar JPG, JPEG, atau PNG yang valid."), 415
                if (actual_format == "JPEG" and extension not in {"jpg", "jpeg"}) or (
                    actual_format == "PNG" and extension != "png"
                ):
                    return jsonify(error="Ekstensi file tidak sesuai dengan format gambar sebenarnya."), 415
                if image.width * image.height > MAX_PHOTO_PIXELS:
                    return jsonify(error="Resolusi foto terlalu besar. Gunakan gambar dengan ukuran piksel lebih kecil."), 413
                image.load()
                oriented = ImageOps.exif_transpose(image)
                if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                    rgba = oriented.convert("RGBA")
                    normalized = Image.new("RGB", rgba.size, "white")
                    normalized.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    normalized = oriented.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return jsonify(error="Gambar tidak valid atau rusak. Pilih foto JPG atau PNG yang dapat dibuka."), 415

    normalized.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    output = BytesIO()
    normalized.save(output, format="JPEG", quality=86, optimize=True)
    while output.tell() > 1024 * 1024 and max(normalized.size) > 320:
        normalized.thumbnail((int(normalized.width * 0.8), int(normalized.height * 0.8)), Image.Resampling.LANCZOS)
        output = BytesIO()
        normalized.save(output, format="JPEG", quality=78, optimize=True)
    photo_data = "data:image/jpeg;base64," + b64encode(output.getvalue()).decode("ascii")
    return jsonify(photo=photo_data, message="Foto berhasil diproses.")


def main():
    address = "127.0.0.1"
    port = 8000
    url = f"http://{address}:{port}"
    print(f"BuildCV berjalan di {url} (tekan Ctrl+C untuk berhenti)")
    webbrowser.open(url)
    app.run(host=address, port=port, debug=False)


if __name__ == "__main__":
    main()