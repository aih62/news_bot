/**
 * 정보보호 통계 대시보드 - 렌더링 엔진
 * =====================================================
 * ▶ 이 파일은 수정하지 않아도 됩니다.
 * ▶ 통계 수치 변경은 dashboard-data.js 만 수정하세요.
 * =====================================================
 */

(function () {
  'use strict';

  /* ── 색상 팔레트 ── */
  const C = {
    cyan:   '#22d3ee',
    green:  '#34d399',
    blue:   '#60a5fa',
    purple: '#a78bfa',
    amber:  '#f59e0b',
    red:    '#f87171',
    teal:   '#10b981',
    gray:   '#64748b',
  };
  const PIE_COLORS = [C.blue, C.amber, C.red, C.gray, C.purple, C.teal, C.green];

  /* ── Chart.js 전역 기본값 ── */
  function initChartDefaults() {
    Chart.defaults.color        = '#64748b';
    Chart.defaults.borderColor  = 'rgba(255,255,255,0.06)';
    Chart.defaults.font.family  = "'JetBrains Mono', monospace";
    Chart.defaults.font.size    = 11;
  }

  /* ── 그라디언트 헬퍼 ── */
  function grad(ctx, color, height) {
    const g = ctx.createLinearGradient(0, 0, 0, height || 250);
    g.addColorStop(0, color + '55');
    g.addColorStop(1, color + '00');
    return g;
  }

  /* ── 차트 생성 헬퍼 ── */
  function mkChart(id, config) {
    const el = document.getElementById(id);
    if (!el) return null;
    return new Chart(el.getContext('2d'), config);
  }

  function lineConfig(labels, datasets, opts) {
    return {
      type: 'line',
      data: { labels, datasets },
      options: Object.assign({
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' } },
        },
        elements: { line: { tension: 0.35 }, point: { radius: 3, hoverRadius: 6 } },
      }, opts || {}),
    };
  }

  function barConfig(labels, datasets, stacked, opts) {
    return {
      type: 'bar',
      data: { labels, datasets },
      options: Object.assign({
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } },
        scales: {
          x: { stacked: !!stacked, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { stacked: !!stacked, grid: { color: 'rgba(255,255,255,0.04)' } },
        },
      }, opts || {}),
    };
  }

  function doughnutConfig(labels, data, colors) {
    return {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{ data, backgroundColor: colors || PIE_COLORS, borderWidth: 0, hoverOffset: 8 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } },
      },
    };
  }

  /* ── KPI 카드 렌더링 ── */
  function renderKPI(data) {
    const container = document.getElementById('db-kpi-container');
    if (!container) return;
    container.innerHTML = '';
    data.kpi.forEach((k, i) => {
      const card = document.createElement('div');
      card.className = 'db-kpi-card';
      card.style.setProperty('--db-card-color', k.color);
      card.style.animationDelay = (i * 0.05) + 's';
      const badge = k.change !== null
        ? `<span class="db-kpi-badge ${k.warn ? 'down' : 'up'}">▲ ${Math.abs(k.change)}%</span>`
        : '';
      card.innerHTML = `
        <div class="db-kpi-label">${k.label}</div>
        <div class="db-kpi-value">${k.value}</div>
        ${badge}
        <div class="db-kpi-year">${k.year} 기준</div>
      `;
      container.appendChild(card);
    });
  }

  /* ── 하이라이트 그리드 렌더링 ── */
  function renderHighlights(containerId, items) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = items.map(h => `
      <div class="db-highlight-item">
        <div class="db-highlight-num" style="color:${h.color}">${h.num}</div>
        <div class="db-highlight-label">${h.label}</div>
      </div>
    `).join('');
  }

  /* ── 테이블 렌더링 ── */
  function renderTable(containerId, items) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = items.map(row => `
      <tr>
        <td style="font-weight:700">${row.country}</td>
        <td><span class="db-tier-badge ${row.tier.toLowerCase().replace(' ', '-')}">${row.tier}</span></td>
        <td style="font-family:'JetBrains Mono', monospace; color:var(--db-cyan)">${row.market}</td>
        <td style="font-size:12px; line-height:1.4">
          <div style="font-weight:600; color:var(--db-text); margin-bottom:2px">${row.strategy}</div>
          <a href="${row.url}" target="_blank" style="color:var(--db-muted); text-decoration:none; font-size:11px"><i class="fas fa-external-link-alt"></i> Original Report</a>
        </td>
      </tr>
    `).join('');
  }

  /* ── AI 산업별 리스크 테이블 렌더링 ── */
  function renderAIIndustryTable(containerId, items) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = items.map(row => `
      <tr>
        <td style="font-weight:700; color:var(--db-cyan)">${row.industry}</td>
        <td style="font-weight:600">${row.threat}</td>
        <td style="font-size:0.85rem; line-height:1.5">${row.detail}</td>
      </tr>
    `).join('');
  }

  /* ── 인사이트 카드 렌더링 ── */
  function renderInsights(containerId, items) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = items.map(box => `
      <a href="${box.url}" target="_blank" class="db-insight-card" style="--accent-color:${box.color}; text-decoration:none">
        <div class="db-insight-icon"><i class="fas ${box.icon}"></i></div>
        <div class="db-insight-value">${box.value}</div>
        <div class="db-insight-title">${box.title}</div>
        <div class="db-insight-sub">${box.sub}</div>
        <div class="db-insight-source">
          <span>${box.source}</span>
          <i class="fas fa-external-link-alt" style="margin-left:5px; font-size:0.8em; opacity:0.7"></i>
        </div>
      </a>
    `).join('');
  }

  /* ── 헤더 렌더링 ── */
  function renderHeader(meta) {
    const el = document.getElementById('db-meta-period');
    if (el) el.textContent = meta.period;
    const base = document.getElementById('db-meta-basedate');
    if (base) base.textContent = '기준일: ' + meta.baseDate;
    const pub = document.getElementById('db-meta-publishdate');
    if (pub) pub.textContent = '발행: ' + meta.publishDate;
  }

  /* ── 메인 카테고리 전환 ── */
  function initMainTabs() {
    document.querySelectorAll('.db-main-tab').forEach(btn => {
      btn.addEventListener('click', function() {
        const target = this.dataset.main;
        document.querySelectorAll('.db-main-tab').forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        document.querySelectorAll('.db-sub-nav-group').forEach(g => g.classList.remove('active'));
        const subGroup = document.getElementById('db-sub-' + target);
        if (subGroup) {
          subGroup.classList.add('active');
          const firstSub = subGroup.querySelector('.db-tab');
          if (firstSub) firstSub.click();
        }
      });
    });
  }

  /* ── 서브 탭 전환 ── */
  function initSubTabs() {
    document.querySelectorAll('.db-tab').forEach(btn => {
      btn.addEventListener('click', function () {
        const target = this.dataset.section;
        document.querySelectorAll('.db-tab').forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        document.querySelectorAll('.db-section').forEach(s => s.classList.remove('active'));
        const sec = document.getElementById('db-section-' + target);
        if (sec) {
          sec.classList.add('active');
          window.dispatchEvent(new Event('resize'));
        }
      });
    });
  }

  /* ── 차트 초기화 ── */
  function initCharts(d) {
    const C2D = (id) => {
      const el = document.getElementById(id);
      return el ? el.getContext('2d') : null;
    };

    /* === 종합 현황 === */

    // 정보보호 산업 매출액 추이
    (function () {
      const ctx = C2D('db-c-revenue');
      if (!ctx) return;
      const r = d.charts.revenue;
      mkChart('db-c-revenue', {
        type: 'line',
        data: {
          labels: r.years,
          datasets: [
            { label: '정보보안', data: r.info, borderColor: C.cyan,   backgroundColor: grad(ctx, C.cyan),   fill: true, borderWidth: 2, pointBackgroundColor: C.cyan },
            { label: '물리보안', data: r.phys, borderColor: C.purple, backgroundColor: grad(ctx, C.purple), fill: true, borderWidth: 2, pointBackgroundColor: C.purple },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 3 } }, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } },
      });
    })();

    // 침해사고 신고접수 추이 (스택 바)
    (function () {
      const i = d.charts.incidents;
      mkChart('db-c-incidents', barConfig(i.years, [
        { label: 'DDoS',   data: i.ddos,       backgroundColor: C.amber  + '88', borderColor: C.amber,  borderWidth: 1 },
        { label: '랜섬웨어', data: i.ransomware, backgroundColor: C.red    + '88', borderColor: C.red,    borderWidth: 1 },
        { label: '서버해킹', data: i.server,     backgroundColor: C.blue   + '88', borderColor: C.blue,   borderWidth: 1 },
        { label: '기타',   data: i.other,       backgroundColor: C.gray   + '88', borderColor: '#94a3b8', borderWidth: 1 },
      ], true));
    })();

    // 도넛 x2
    mkChart('db-c-share', doughnutConfig(d.charts.revenueShare.labels, d.charts.revenueShare.data, [C.cyan, C.purple]));
    mkChart('db-c-incident-share', doughnutConfig(d.charts.incidentShare.labels, d.charts.incidentShare.data, [C.blue, C.amber, C.red, C.gray]));

    // 글로벌 랜섬웨어 피해 규모
    (function () {
      const ctx = C2D('db-c-ransomware');
      if (!ctx) return;
      const r = d.charts.ransomware;
      mkChart('db-c-ransomware', {
        type: 'line',
        data: {
          labels: r.years,
          datasets: [{
            label: '피해규모',
            data: r.values,
            borderColor: C.red,
            backgroundColor: grad(ctx, C.red),
            fill: true,
            borderWidth: 2,
            pointBackgroundColor: r.values.map((_, i) => i >= r.estimateFrom ? C.red + '66' : C.red),
            segment: { borderDash: (ctx) => ctx.p1DataIndex >= r.estimateFrom ? [4, 4] : [] },
          }],
        },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.3 }, point: { radius: 3 } }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } },
      });
    })();

    /* === 산업 탭 === */

    // 연도별 매출액
    (function () {
      const ctx = C2D('db-c-rev2');
      if (!ctx) return;
      const r = d.charts.revenue;
      mkChart('db-c-rev2', {
        type: 'line',
        data: {
          labels: r.years,
          datasets: [
            { label: '정보보안', data: r.info, borderColor: C.cyan,   backgroundColor: grad(ctx, C.cyan, 280),   fill: true, borderWidth: 2, pointBackgroundColor: C.cyan },
            { label: '물리보안', data: r.phys, borderColor: C.purple, backgroundColor: grad(ctx, C.purple, 280), fill: true, borderWidth: 2, pointBackgroundColor: C.purple },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 3 } }, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } },
      });
    })();

    // 수출액
    (function () {
      const e = d.charts.exports;
      mkChart('db-c-export', barConfig(e.years, [
        { label: '정보보안', data: e.info, backgroundColor: C.cyan   + '88', borderColor: C.cyan,   borderWidth: 1 },
        { label: '물리보안', data: e.phys, backgroundColor: C.purple + '88', borderColor: C.purple, borderWidth: 1 },
      ]));
    })();

    // 기업 수 추이
    (function () {
      const c = d.charts.companies;
      mkChart('db-c-companies', barConfig(c.years, [
        { label: '정보보안', data: c.info, backgroundColor: C.cyan   + '88', borderColor: C.cyan,   borderWidth: 1 },
        { label: '물리보안', data: c.phys, backgroundColor: C.purple + '88', borderColor: C.purple, borderWidth: 1 },
      ]));
    })();

    // 글로벌 시장 규모
    (function () {
      const ctx = C2D('db-c-global');
      if (!ctx) return;
      const g = d.charts.globalMarket;
      mkChart('db-c-global', {
        type: 'line',
        data: {
          labels: g.years,
          datasets: [
            { label: '전체',   data: g.total, borderColor: C.green,  backgroundColor: grad(ctx, C.green), fill: true, borderWidth: 2, pointBackgroundColor: C.green },
            { label: '정보보안', data: g.info,  borderColor: C.cyan,   borderWidth: 2, pointBackgroundColor: C.cyan },
            { label: '물리보안', data: g.phys,  borderColor: C.purple, borderWidth: 2, pointBackgroundColor: C.purple },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 3 } }, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } },
      });
    })();

    // 수출 권역별 도넛
    mkChart('db-c-export-region-info', doughnutConfig(d.charts.exportRegionInfo.labels, d.charts.exportRegionInfo.data));
    mkChart('db-c-export-region-phys', doughnutConfig(d.charts.exportRegionPhys.labels, d.charts.exportRegionPhys.data));

    /* === 침해사고 탭 === */

    // 유형별 추이 스택 바
    (function () {
      const b = d.charts.breachTypes;
      mkChart('db-c-breach-types', barConfig(b.years, [
        { label: 'DDoS',   data: b.ddos,       backgroundColor: C.amber  + '88', borderColor: C.amber,  borderWidth: 1 },
        { label: '랜섬웨어', data: b.ransomware, backgroundColor: C.red    + '88', borderColor: C.red,    borderWidth: 1 },
        { label: '서버해킹', data: b.server,     backgroundColor: C.blue   + '88', borderColor: C.blue,   borderWidth: 1 },
        { label: '기타',   data: b.other,       backgroundColor: C.gray   + '88', borderColor: '#94a3b8', borderWidth: 1 },
      ], true));
    })();

    // 침해 탐지 도넛
    mkChart('db-c-detect-share', doughnutConfig(d.charts.detectShare.labels, d.charts.detectShare.data, [C.amber, C.red]));

    // 글로벌 악성코드 수 추이
    (function () {
      const ctx = C2D('db-c-malware');
      if (!ctx) return;
      const m = d.charts.malware;
      mkChart('db-c-malware', {
        type: 'line',
        data: { labels: m.years, datasets: [{ label: '글로벌 악성코드(백만)', data: m.values, borderColor: C.red, backgroundColor: grad(ctx, C.red), fill: true, borderWidth: 2, pointBackgroundColor: C.red }] },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 3 } }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } },
      });
    })();

    // DDoS 대피소
    (function () {
      const dd = d.charts.ddosRefuge;
      mkChart('db-c-ddos', barConfig(dd.years, [
        { label: '이용업체수', data: dd.values, backgroundColor: C.cyan + '88', borderColor: C.cyan, borderWidth: 1 },
      ]));
    })();

    // 침해 경험률
    (function () {
      const ctx = C2D('db-c-breach-rate');
      if (!ctx) return;
      const br = d.charts.breachRate;
      mkChart('db-c-breach-rate', {
        type: 'line',
        data: { labels: br.years, datasets: [{ label: '침해경험률(%)', data: br.values, borderColor: C.red, backgroundColor: grad(ctx, C.red, 160), fill: true, borderWidth: 2, pointBackgroundColor: C.red }] },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 4 } }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, min: 0 } } },
      });
    })();

    /* === 인력 탭 === */

    // 인력 추이
    (function () {
      const w = d.charts.workforce;
      mkChart('db-c-workforce', barConfig(w.years, [
        { label: '정보보안', data: w.info, backgroundColor: C.cyan   + '88', borderColor: C.cyan,   borderWidth: 1 },
        { label: '물리보안', data: w.phys, backgroundColor: C.purple + '88', borderColor: C.purple, borderWidth: 1 },
      ]));
    })();

    // 사이버 인재 양성 누적
    (function () {
      const ctx = C2D('db-c-talent');
      if (!ctx) return;
      const t = d.charts.talent;
      mkChart('db-c-talent', {
        type: 'line',
        data: { labels: t.years, datasets: [{ label: '누적 양성인원', data: t.values, borderColor: C.green, backgroundColor: grad(ctx, C.green, 280), fill: true, borderWidth: 2, pointBackgroundColor: C.green }] },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 4 } }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, min: 0 } } },
      });
    })();

    // 인력 수요 전망
    (function () {
      const dm = d.charts.demand;
      mkChart('db-c-demand', barConfig(dm.labels, [
        { label: '2021년', data: dm.y2021, backgroundColor: C.blue  + '88', borderColor: C.blue,  borderWidth: 1 },
        { label: '2026년', data: dm.y2026, backgroundColor: C.cyan  + '88', borderColor: C.cyan,  borderWidth: 1 },
      ]));
    })();

    // 정보보호학과 현황
    (function () {
      const ed = d.charts.education;
      mkChart('db-c-education', barConfig(ed.labels, [
        { label: '학과수',      data: ed.dept,     backgroundColor: C.purple + '88', borderColor: C.purple, borderWidth: 1 },
        { label: '학생수(÷100)', data: ed.students, backgroundColor: C.cyan   + '88', borderColor: C.cyan,   borderWidth: 1 },
      ]));
    })();

    /* === 인증 탭 === */

    // ISMS 추이
    (function () {
      const ctx = C2D('db-c-isms');
      if (!ctx) return;
      const is = d.charts.isms;
      mkChart('db-c-isms', {
        type: 'line',
        data: { labels: is.years, datasets: [{ label: 'ISMS 인증', data: is.values, borderColor: C.teal, backgroundColor: grad(ctx, C.teal), fill: true, borderWidth: 2, pointBackgroundColor: C.teal }] },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 3 } }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, min: 500 } } },
      });
    })();

    // 클라우드 보안인증 스택 바
    (function () {
      const cc = d.charts.cloudCert;
      mkChart('db-c-cloud', barConfig(cc.years, [
        { label: 'IaaS', data: cc.iaas, backgroundColor: C.cyan   + '88', borderColor: C.cyan,   borderWidth: 1 },
        { label: 'SaaS', data: cc.saas, backgroundColor: C.blue   + '88', borderColor: C.blue,   borderWidth: 1 },
        { label: 'DaaS', data: cc.daas, backgroundColor: C.purple + '88', borderColor: C.purple, borderWidth: 1 },
      ], true));
    })();

    // IoT 보안인증
    (function () {
      const ctx = C2D('db-c-iot');
      if (!ctx) return;
      const io = d.charts.iotCert;
      mkChart('db-c-iot', {
        type: 'line',
        data: { labels: io.years, datasets: [{ label: 'IoT 인증건수', data: io.values, borderColor: C.amber, backgroundColor: grad(ctx, C.amber), fill: true, borderWidth: 2, pointBackgroundColor: C.amber }] },
        options: { responsive: true, maintainAspectRatio: false, elements: { line: { tension: 0.35 }, point: { radius: 3 } }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, min: 0 } } },
      });
    })();

    // 공시 이행기업 & IT 예산 혼합
    (function () {
      const disc = d.charts.disclosure;
      mkChart('db-c-disclosure', {
        type: 'bar',
        data: {
          labels: disc.years,
          datasets: [
            { label: '이행기업수', data: disc.companies, backgroundColor: C.cyan + '88', borderColor: C.cyan, borderWidth: 1, yAxisID: 'y' },
            { label: 'IT예산 투자비중(%)', data: disc.budgetRatio, backgroundColor: C.amber + 'dd', borderColor: C.amber, borderWidth: 1, type: 'line', yAxisID: 'y2', fill: false, pointBackgroundColor: C.amber },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, position: 'left' }, y2: { position: 'right', grid: { drawOnChartArea: false }, min: 0, max: 10 } } },
      });
    })();

    /* === 예방 탭 === */

    // C-TAS 혼합
    (function () {
      const ct = d.charts.ctas;
      mkChart('db-c-ctas', {
        type: 'bar',
        data: {
          labels: ct.years,
          datasets: [
            { label: '참여기업(개)', data: ct.companies, backgroundColor: C.cyan  + '88', borderColor: C.cyan,  borderWidth: 1, yAxisID: 'y' },
            { label: '공유건수(억건)', data: ct.shared,   backgroundColor: C.green + 'dd', borderColor: C.green, borderWidth: 1, type: 'line', fill: false, yAxisID: 'y2', pointBackgroundColor: C.green },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, position: 'left' }, y2: { position: 'right', grid: { drawOnChartArea: false }, min: 0 } } },
      });
    })();

    // 모의훈련 혼합
    (function () {
      const dr = d.charts.drill;
      mkChart('db-c-drill', {
        type: 'bar',
        data: {
          labels: dr.years,
          datasets: [
            { label: '참여기업(개)', data: dr.companies, backgroundColor: C.blue   + '88', borderColor: C.blue,   borderWidth: 1, yAxisID: 'y' },
            { label: '참여인원(명÷100)', data: dr.personnel, backgroundColor: C.purple, borderColor: C.purple, borderWidth: 1, type: 'line', fill: false, yAxisID: 'y2', pointBackgroundColor: C.purple },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' }, position: 'left' }, y2: { position: 'right', grid: { drawOnChartArea: false }, min: 0 } } },
      });
    })();

    // 악성코드 모니터링 스택 바
    (function () {
      const mm = d.charts.malMon;
      mkChart('db-c-malmon', barConfig(mm.years, [
        { label: '유포지', data: mm.source, backgroundColor: C.red   + '88', borderColor: C.red,   borderWidth: 1 },
        { label: '경유지', data: mm.relay,  backgroundColor: C.amber + '88', borderColor: C.amber, borderWidth: 1 },
      ], true));
    })();

    // 중소기업 보안 지원
    (function () {
      const sme = d.charts.sme;
      mkChart('db-c-sme', barConfig(sme.years, [
        { label: '보안컨설팅·솔루션', data: sme.consulting, backgroundColor: C.cyan   + '88', borderColor: C.cyan,   borderWidth: 1 },
        { label: '클라우드보안',      data: sme.cloud,      backgroundColor: C.purple + '88', borderColor: C.purple, borderWidth: 1 },
      ]));
    })();

    /* === 글로벌 탭 === */

    // 글로벌 사이버보안 지표 추이 1 (시장규모 vs AI 공격탐지)
    (function () {
      const g = d.charts.globalMarketTrend;
      mkChart('db-c-global-market-cost', {
        type: 'bar',
        data: {
          labels: g.years,
          datasets: [
            { label: '시장규모($B)', data: g.marketSize, backgroundColor: C.cyan + '88', borderColor: C.cyan, borderWidth: 1, yAxisID: 'y' },
            { label: 'AI 공격탐지(%)', data: g.aiAttackDetection, backgroundColor: C.red + 'dd', borderColor: C.red, borderWidth: 2, type: 'line', fill: false, yAxisID: 'y2', pointBackgroundColor: C.red },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { title: { display: true, text: 'USD Billion' }, grid: { color: 'rgba(255,255,255,0.04)' }, position: 'left' }, y2: { title: { display: true, text: 'Percent (%)' }, position: 'right', grid: { drawOnChartArea: false }, min: 0, max: 100 } } },
      });
    })();

    // 글로벌 사이버보안 지표 추이 2 (인력격차 vs 국가전략)
    (function () {
      const g = d.charts.globalMarketTrend;
      mkChart('db-c-global-workforce-cloud', {
        type: 'bar',
        data: {
          labels: g.years,
          datasets: [
            { label: '인력격차(백만)', data: g.workforceGap, backgroundColor: C.amber + '88', borderColor: C.amber, borderWidth: 1, yAxisID: 'y' },
            { label: '사이버전략수립(%)', data: g.nationalStrategy, backgroundColor: C.purple + 'dd', borderColor: C.purple, borderWidth: 2, type: 'line', fill: false, yAxisID: 'y2', pointBackgroundColor: C.purple },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { title: { display: true, text: 'Million People' }, grid: { color: 'rgba(255,255,255,0.04)' }, position: 'left' }, y2: { title: { display: true, text: 'Percent (%)' }, position: 'right', grid: { drawOnChartArea: false }, min: 0, max: 100 } } },
      });
    })();
    // 전 세계 사이버 범죄 비용 추이
    (function () {
      const cc = d.charts.cybercrimeCost;
      mkChart('db-c-cybercrime-cost', {
        type: 'line',
        data: {
          labels: cc.years,
          datasets: [{
            label: '사이버 범죄 피해액 ($T)',
            data: cc.values,
            borderColor: C.red,
            backgroundColor: C.red + '22',
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: C.red,
            pointRadius: 4,
            segment: {
              borderDash: ctx => cc.estimateFrom !== undefined && ctx.p1DataIndex >= cc.estimateFrom ? [6, 6] : [],
            }
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { title: { display: true, text: 'Trillion USD ($T)' }, grid: { color: 'rgba(255,255,255,0.04)' } } } }
      });
    })();

    // 지역별 주간 평균 공격 수
    (function () {
      const ar = d.charts.attacksByRegion;
      mkChart('db-c-attacks-region', {
        type: 'bar',
        data: {
          labels: ar.labels,
          datasets: [{
            label: '주간 평균 공격 수',
            data: ar.data,
            backgroundColor: [C.red + '88', C.amber + '88', C.purple + '88', C.blue + '88', C.cyan + '88'],
            borderColor: [C.red, C.amber, C.purple, C.blue, C.cyan],
            borderWidth: 1
          }]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { display: false } } } }
      });
    })();

    // 산업별 주간 평균 공격 수
    (function () {
      const ai = d.charts.attacksByIndustry;
      mkChart('db-c-attacks-industry', {
        type: 'bar',
        data: {
          labels: ai.labels,
          datasets: [{
            label: '주간 평균 공격 수',
            data: ai.data,
            backgroundColor: C.cyan + '88',
            borderColor: C.cyan,
            borderWidth: 1
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } }
      });
    })();
    // 글로벌 사이버 범죄 손실(초당) 3개년 추이
    (function () {
      const gt = d.charts.globalDetailedTrends;
      mkChart('db-c-trend-cost-sec', {
        type: 'line',
        data: {
          labels: gt.years,
          datasets: [{
            label: '초당 손실액 (k$)',
            data: gt.costPerSec,
            borderColor: C.red,
            backgroundColor: C.red + '22',
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: C.red,
            pointRadius: 5
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { title: { display: true, text: 'USD Thousand (k$)' }, grid: { color: 'rgba(255,255,255,0.04)' } } } }
      });
    })();

    // 글로벌 공격 빈도 및 간격 3개년 추이
    (function () {
      const gt = d.charts.globalDetailedTrends;
      mkChart('db-c-trend-frequency', {
        type: 'bar',
        data: {
          labels: gt.years,
          datasets: [
            { label: '주간 평균 공격(건)', data: gt.weeklyAttacks, backgroundColor: C.blue + '88', borderColor: C.blue, borderWidth: 1, yAxisID: 'y' },
            { label: '공격 발생 간격(초)', data: gt.attackInterval, backgroundColor: C.purple, borderColor: C.purple, borderWidth: 2, type: 'line', fill: false, yAxisID: 'y2', pointBackgroundColor: C.purple }
          ]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { title: { display: true, text: 'Attacks (Counts)' }, position: 'left', grid: { color: 'rgba(255,255,255,0.04)' } }, y2: { title: { display: true, text: 'Interval (Sec)' }, position: 'right', grid: { drawOnChartArea: false }, min: 30 } } }
      });
    })();

    // 글로벌 공격 대상 국가 TOP 10 테이블
    (function () {
      const list = d.charts.topTargeted2025;
      const el = document.getElementById('db-c-table-targeted');
      if (!el) return;
      el.innerHTML = list.map(row => `
        <tr>
          <td style="text-align:center; font-weight:700; color:var(--db-accent)">${row.rank}</td>
          <td style="font-weight:700">${row.icon} ${row.country}</td>
          <td style="font-size:0.85rem">${row.reason}</td>
        </tr>
      `).join('');
    })();

    // 글로벌 랜섬웨어 산업별 비중 테이블
    (function () {
      const list = d.charts.ransomwareIndustryShare || [];
      const el = document.getElementById('db-c-table-industry-share');
      if (!el) return;
      el.innerHTML = list.map(row => `
        <tr>
          <td style="text-align:center; font-weight:700">${row.rank}</td>
          <td style="font-weight:700">${row.industry}</td>
          <td style="text-align:center; color:var(--db-accent)">${row.share}</td>
          <td style="text-align:center; color:${row.change.includes('+') ? 'var(--db-red)' : 'var(--db-green)'}">${row.change}</td>
          <td style="font-size:0.85rem">${row.reason}</td>
        </tr>
      `).join('');
    })();

    // 글로벌 랜섬웨어 산업별 공격 건수 테이블
    (function () {
      const list = d.charts.ransomwareIndustryCount || [];
      const el = document.getElementById('db-c-table-industry-count');
      if (!el) return;
      el.innerHTML = list.map(row => `
        <tr>
          <td style="text-align:center; font-weight:700">${row.rank}</td>
          <td style="font-weight:700">${row.industry}</td>
          <td style="text-align:center; color:var(--db-cyan)">${row.count}</td>
          <td style="text-align:center">${row.change}</td>
          <td style="font-size:0.85rem">${row.note}</td>
        </tr>
      `).join('');
    })();

    // 국내 산업별 위협 순위 테이블
    (function () {
      const list = d.charts.domesticIndustryStats2025 || [];
      const el = document.getElementById('db-c-table-industry-domestic');
      if (!el) return;
      el.innerHTML = list.map(row => `
        <tr>
          <td style="text-align:center; font-weight:700; color:var(--db-accent)">${row.rank}</td>
          <td style="font-weight:700">${row.industry}</td>
          <td style="font-size:0.85rem">${row.feature}</td>
        </tr>
      `).join('');
    })();

    // 랜섬웨어 지역별/산업별 비중 도넛
    mkChart('db-c-ransomware-region', doughnutConfig(d.charts.ransomwareStats.regional.labels, d.charts.ransomwareStats.regional.data, [C.red, C.purple, C.blue, C.gray]));
    mkChart('db-c-ransomware-industry', doughnutConfig(d.charts.ransomwareStats.industry.labels, d.charts.ransomwareStats.industry.data, [C.amber, C.teal, C.gray]));

    // 대륙별 비중 도넛
    mkChart('db-c-regional-share', doughnutConfig(d.charts.regionalShare.labels, d.charts.regionalShare.data, [C.blue, C.purple, C.cyan, C.amber]));

    // 대륙별 성장률 바
    (function () {
      const r = d.charts.regionalCAGR;
      mkChart('db-c-regional-cagr', barConfig(r.labels, [
        { label: 'CAGR (24-26, %)', data: r.data, backgroundColor: [C.blue + '88', C.purple + '88', C.cyan + '88', C.amber + '88'], borderColor: [C.blue, C.purple, C.cyan, C.amber], borderWidth: 1 },
      ]));
    })();

    /* === AI 분야 탭 === */

    // AI 보안 시장 성장 전망
    (function () {
      const ctx = C2D('db-c-ai-market-growth');
      if (!ctx) return;
      const g = d.charts.aiMarketGrowth;
      mkChart('db-c-ai-market-growth', {
        type: 'line',
        data: {
          labels: g.years,
          datasets: [{
            label: '시장규모 ($B)',
            data: g.values,
            borderColor: C.cyan,
            backgroundColor: grad(ctx, C.cyan),
            fill: true,
            borderWidth: 2,
            pointBackgroundColor: g.values.map((_, i) => i >= g.estimateFrom ? C.cyan + '66' : C.cyan),
            segment: { borderDash: (ctx) => ctx.p1DataIndex >= g.estimateFrom ? [4, 4] : [] },
          }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { color: 'rgba(255,255,255,0.04)' } } } },
      });
    })();

    // AI 악용 공격 성공률 및 위협 지표
    (function () {
      const s = d.charts.aiSuccessRates;
      mkChart('db-c-ai-success-rates', {
        type: 'bar',
        data: {
          labels: s.labels,
          datasets: [{
            label: '비율/성공률 (%)',
            data: s.data,
            backgroundColor: [C.red + '88', C.purple + '88', C.amber + '88', C.blue + '88', C.cyan + '88'],
            borderColor: [C.red, C.purple, C.amber, C.blue, C.cyan],
            borderWidth: 1
          }]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { max: 100, grid: { color: 'rgba(255,255,255,0.04)' } }, y: { grid: { display: false } } } }
      });
    })();

    // AI 위협 주요 지표 3개년 추이
    (function () {
      const t = d.charts.aiAttackTrends;
      mkChart('db-c-ai-attack-trends', {
        type: 'line',
        data: {
          labels: t.years,
          datasets: [
            { label: '공격 건수 (백만건)', data: t.attackCounts, borderColor: C.red, borderWidth: 3, yAxisID: 'y' },
            { label: 'AI 연계 비중 (%)', data: t.aiShare, borderColor: C.purple, borderWidth: 3, yAxisID: 'y2' },
            { label: '피싱 증가율 (%)', data: t.phishingGrowth, borderColor: C.amber, borderDash: [5, 5], borderWidth: 2, yAxisID: 'y2' }
          ]
        },
        options: { 
          responsive: true, 
          maintainAspectRatio: false, 
          plugins: { legend: { position: 'bottom' } }, 
          scales: { 
            y: { position: 'left', title: { display: true, text: 'Counts (M)' } }, 
            y2: { position: 'right', title: { display: true, text: 'Percentage (%)' }, grid: { drawOnChartArea: false } } 
          } 
        }
      });
    })();
  }

  /* ── 초기화 ── */
  function init() {
    if (typeof DASHBOARD_DATA === 'undefined') {
      console.error('[Dashboard] DASHBOARD_DATA not loaded. Check dashboard-data.js');
      return;
    }
    if (typeof Chart === 'undefined') {
      console.error('[Dashboard] Chart.js not loaded.');
      return;
    }
    initChartDefaults();
    renderHeader(DASHBOARD_DATA.meta);
    renderKPI(DASHBOARD_DATA);
    renderHighlights('db-highlights-incidents', DASHBOARD_DATA.charts.incidentHighlights);
    renderHighlights('db-highlights-cert',      DASHBOARD_DATA.charts.certHighlights);
    renderHighlights('db-highlights-prevent',   DASHBOARD_DATA.charts.preventHighlights);
    renderHighlights('db-highlights-global',    DASHBOARD_DATA.charts.globalHighlights);
    renderHighlights('db-highlights-ai',        DASHBOARD_DATA.charts.aiHighlights);
    renderTable('db-table-countries',           DASHBOARD_DATA.charts.countryStats);
    renderAIIndustryTable('db-c-table-ai-industry', DASHBOARD_DATA.charts.aiIndustryInsights);
    renderInsights('db-insights-grid',          DASHBOARD_DATA.charts.top10Insights);
    initMainTabs();
    initSubTabs();
    initCharts(DASHBOARD_DATA);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
