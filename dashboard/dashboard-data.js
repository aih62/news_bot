/**
 * 정보보호 통계 대시보드 - 데이터 파일
 * =====================================================
 * ▶ 이 파일만 수정하면 대시보드의 모든 통계 수치가 업데이트됩니다.
 * ▶ 기준일 / 발행일 / KPI 카드 / 차트 데이터를 모두 여기서 관리합니다.
 * =====================================================
 */

const DASHBOARD_DATA = {

  // ── 메타 정보 ──────────────────────────────────────────
  meta: {
    title: '사이버보안 대시보드',
    period: '2026년 2월',
    baseDate: '',
    publishDate: '',
    source: '',
  },

  // ── KPI 카드 (종합 현황) ───────────────────────────────
  // change: null 이면 증감 배지 숨김 / warn: true 이면 빨간색 배지
  kpi: [
    { label: '정보보호 산업 총매출',  value: '18.6조원', change: 10.5, year: '2024',      color: '#22d3ee' },
    { label: '정보보안 매출',         value: '7.12조원', change: 16.1, year: '2024',      color: '#34d399' },
    { label: '정보보호 수출액',       value: '1.87조원', change: 11.4, year: '2024',      color: '#60a5fa' },
    { label: '정보보호 기업 수',      value: '1,780개',  change:  4.2, year: '2024',      color: '#a78bfa' },
    { label: '정보보호 산업 인력',    value: '66,367명', change: 10.0, year: '2024',      color: '#f59e0b' },
    { label: '침해사고 신고 (2월)',   value: '415건',    change: null, year: '2026년 2월', color: '#f87171', warn: true },
    { label: 'ISMS 인증 건수',        value: '1,257건',  change:  0.4, year: '2026년 2월', color: '#10b981' },
    { label: 'C-TAS 참여기업',        value: '5,371개',  change:  2.7, year: '2026년 2월', color: '#06b6d4' },
  ],

  // ── 종합 현황 탭 차트 ─────────────────────────────────
  charts: {

    // 정보보호 산업 매출액 추이 (선)
    revenue: {
      years: [2020, 2021, 2022, 2023, 2024],
      info:  [39000, 49000, 56172, 61455, 71244],   // 정보보안 (억원)
      phys:  [79986, 89611, 105632, 106856, 114701], // 물리보안 (억원)
    },

    // 침해사고 신고접수 추이 (스택 바)
    incidents: {
      years: [2022, 2023, 2024, 2025],
      ddos:       [122,  213,  285,  588],
      ransomware: [325,  258,  195,  274],
      server:     [585,  583, 1057, 1053],
      other:      [110,  223,  350,  468],
    },

    // 2024년 매출 비중 도넛
    revenueShare: {
      labels: ['정보보안', '물리보안'],
      data:   [38.3, 61.7],
    },

    // 2026년 2월 침해신고 유형 도넛
    incidentShare: {
      labels: ['서버해킹', 'DDoS공격', '랜섬웨어', '기타'],
      data:   [153, 131, 68, 63],
    },

    // 글로벌 랜섬웨어 피해 규모 (선, 추정값 포함)
    ransomware: {
      years:    [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028],
      values:   [80,   115,  200,  240,  300,  420,  570,  740,  970,  1250],
      // 이 인덱스부터 점선(추정값)으로 표시
      estimateFrom: 5,
    },

    // ── 산업 탭 ──────────────────────────────────────────

    // 연도별 정보보호 기업 수 (바)
    companies: {
      years: [2020, 2021, 2022, 2023, 2024],
      info:  [531, 669, 737, 814, 876],  // 정보보안
      phys:  [752, 848, 857, 894, 904],  // 물리보안
    },

    // 연도별 정보보호 수출액 (바, 억원)
    exports: {
      years: [2020, 2021, 2022, 2023, 2024],
      info:  [1456, 1526, 1553, 1478, 1243],  // 정보보안
      phys:  [17679, 19242, 18515, 15322, 17479], // 물리보안
    },

    // 글로벌 정보보호 시장 규모 (선, 억 달러)
    globalMarket: {
      years:   [2023, 2024, '2025E', '2030E'],
      total:   [3006, 3233, 3482, 5034],
      info:    [1904, 2079, 2275, 3519],
      phys:    [1102, 1152, 1207, 1515],
    },

    // 2024년 정보보안 수출 권역별 비중 (도넛, %)
    exportRegionInfo: {
      labels: ['미국', '일본', '중국', '유럽', '기타'],
      data:   [9.2, 32.0, 10.6, 3.2, 45.0],
    },

    // 2024년 물리보안 수출 권역별 비중 (도넛, %)
    exportRegionPhys: {
      labels: ['미국', '일본', '중국', '유럽', '기타'],
      data:   [35.1, 7.2, 1.4, 13.9, 42.4],
    },

    // ── 침해사고 탭 ──────────────────────────────────────

    // 침해사고 신고접수 유형별 추이 (스택 바)
    breachTypes: {
      years: [2022, 2023, 2024, 2025],
      ddos:       [122,  213,  285, 588],
      ransomware: [325,  258,  195, 274],
      server:     [585,  583, 1057, 1053],
      other:      [110,  223,  350, 468],
    },

    // 2026년 2월 침해탐지 비중 도넛
    detectShare: {
      labels: ['스미싱 문자', '홈페이지 악성코드'],
      data:   [9364, 4720],
    },

    // 글로벌 악성코드 수 추이 (선, 백만 개)
    malware: {
      years:  [2020, 2021, 2022, 2023, 2024, 2025, 2026],
      values: [968,  1128, 1228, 1338, 1443, 1548, 1557],
    },

    // DDoS 사이버대피소 이용 업체 수 (바)
    ddosRefuge: {
      years:  [2022, 2023, 2024, 2025],
      values: [11075, 17010, 18036, 20224],
    },

    // 국내 기업 침해사고 경험률 (선, %)
    breachRate: {
      years:  [2019, 2020, 2021, 2022, 2023, 2024],
      values: [2.8,  2.0,  1.0,  3.7,  1.3,  0.3],
    },

    // 침해탐지 하이라이트 수치
    incidentHighlights: [
      { num: '415건',    color: '#f87171', label: '2026년 2월 침해신고' },
      { num: '14,084건', color: '#f59e0b', label: '2월 침해탐지 합계' },
      { num: '2,940건',  color: '#f87171', label: '2월 피싱·파밍 차단' },
      { num: '1,557M',   color: '#a78bfa', label: '글로벌 악성코드 수 (백만)' },
    ],

    // ── 인력 탭 ──────────────────────────────────────────

    // 정보보호 산업 인력 추이 (바)
    workforce: {
      years: [2021, 2022, 2023, 2024],
      info:  [17699, 22997, 23947, 23987],
      phys:  [45863, 41834, 36361, 42380],
    },

    // 사이버 10만 인재 양성 누적 실적 (선)
    talent: {
      years:  [2022, 2023, 2024, 2025, 2026],
      values: [10677, 31823, 56859, 81979, 104032],
    },

    // 사이버 인력 수요 전망 (바)
    demand: {
      labels:    ['제품개발', '보안관리', '사고대응'],
      y2021:     [13000, 95000, 13000],
      y2026:     [17000, 124000, 18000],
    },

    // 정보보호학과 현황 2024 (바)
    education: {
      labels:   ['대학', '대학원', '전문대학'],
      dept:     [47, 58, 9],       // 학과 수
      students: [53, 15, 2],       // 학생 수 ÷ 100
    },

    // ── 인증 탭 ──────────────────────────────────────────

    // ISMS 인증 건수 추이 (선)
    isms: {
      years:  [2019, 2020, 2021, 2022, 2023, 2024, 2025],
      values: [755,  835,  936,  953, 1073, 1124, 1252],
    },

    // 클라우드 보안인증 추이 (스택 바)
    cloudCert: {
      years: [2019, 2020, 2021, 2022, 2023, 2024, 2025],
      iaas:  [9, 10, 9,  9,  9,  10,  15],
      saas:  [9, 16, 38, 63, 92, 142, 178],
      daas:  [0, 0,  0,  0,  4,   5,   5],
    },

    // IoT 보안인증 추이 (선)
    iotCert: {
      years:  [2019, 2020, 2021, 2022, 2023, 2024, 2025],
      values: [24, 41, 73, 83, 82, 106, 106],
    },

    // 정보보호 공시 이행기업 & IT예산 투자비중 (혼합)
    disclosure: {
      years:         [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
      companies:     [20, 30, 45, 64, 658, 715, 746, 773],
      budgetRatio:   [4.1, 4.3, 4.9, 5.6, 6.0, 6.1, 6.1, 6.3], // IT 예산 중 정보보호 비중(%)
    },

    // 인증 하이라이트 수치
    certHighlights: [
      { num: '1,257건',  color: '#34d399', label: 'ISMS 인증 (2026.2월)' },
      { num: '27,928건', color: '#60a5fa', label: 'CISO 신고 기업 (2026.2월)' },
      { num: '194건',    color: '#a78bfa', label: '클라우드 보안인증 (2026.2월)' },
      { num: '773개',    color: '#22d3ee', label: '정보보호 공시 기업 (2025)' },
    ],

    // ── 예방 탭 ──────────────────────────────────────────

    // C-TAS 참여기업 및 공유건수 추이 (혼합)
    ctas: {
      years:     [2021, 2022, 2023, 2024, 2025],
      companies: [332,  2161, 3432, 4408, 5231], // 참여기업(개)
      shared:    [3.2,  4.2,  5.7,  8.2, 11.8],  // 공유건수(억건)
    },

    // 사이버위기 대응 모의훈련 (혼합)
    drill: {
      years:     [2021, 2022, 2023, 2024, 2025],
      companies: [404,  660,  1217, 2066, 3143], // 참여기업(개)
      personnel: [1978, 2649, 4126, 5716, 7145], // 참여인원(명÷100)
    },

    // 홈페이지 악성코드 모니터링 (스택 바)
    malMon: {
      years:  [2022, 2023, 2024, 2025],
      source: [4354,  7307, 13072, 22087], // 유포지
      relay:  [9307,  5424,   895,   486], // 경유지
    },

    // 중소·영세기업 보안 지원 (바)
    sme: {
      years:       [2022, 2023, 2024, 2025],
      consulting:  [605,  324,  246,  80],  // 보안컨설팅·솔루션
      cloud:       [730, 1231,  607, 408],  // 클라우드보안
    },

    // 예방 하이라이트 수치
    preventHighlights: [
      { num: '5,371개',  color: '#22d3ee', label: 'C-TAS 참여기업 (2026.2월)' },
      { num: '12.7억건', color: '#34d399', label: 'C-TAS 공유건수 (2026.2월)' },
      { num: '74개',     color: '#60a5fa', label: '모의훈련 참여기업 (2026.2월)' },
      { num: '545건',    color: '#a78bfa', label: '해킹사고 분석지원 (2026.2월)' },
    ],

    // ── 글로벌 탭 ──────────────────────────────────────────

    // 글로벌 사이버보안 시장 규모 및 추이 ($B)
    globalMarketTrend: {
      years: [2023, 2024, 2025, 2026],
      marketSize: [185.4, 208.8, 239.5, 275.2], // 시장 규모 ($B)
      aiAttackDetection: [12.0, 28.0, 44.0, 65.0], // AI 기반 공격 탐지 비중 (%)
      workforceGap: [4.0, 4.8, 5.6, 6.5],       // 인력 부족 격차 (백만명)
      nationalStrategy: [82.0, 88.0, 92.0, 95.0],  // 국가 사이버 전략 수립국 (%)
    },

    // 전 세계 사이버 범죄 비용 추이 ($T, 조 달러)
    // 출처: Cybersecurity Ventures
    cybercrimeCost: {
      years: [2015, 2024, 2025, 2030],
      values: [3.0, 9.5, 10.5, 15.0],
      estimateFrom: 1, // 2024년부터 전망/추정치
    },

    // 지역별 기업당 주간 평균 공격 수 (2024 Q3 업데이트)
    // 출처: Check Point Research (Q3 2024)
    attacksByRegion: {
      labels: ['아프리카', '아시아·태평양', '라틴아메리카', '유럽', '북미'],
      data: [3370, 2863, 2844, 1557, 1298],
      increase: [90, 55, 72, 86, 55], // 전년 대비 증가율 (%)
    },

    // 산업별 기업당 주간 평균 공격 수 (2024 Q2)
    attacksByIndustry: {
      labels: ['교육·연구', '정부·군', '의료', '통신', '제조업'],
      data: [3341, 2084, 1999, 1912, 1636],
    },

    // 2025년 가장 많이 공격받는 국가 TOP 10 (Projected)
    // 출처: DeepStrike 2025 / IBM / Radware 종합
    topTargeted2025: [
      { rank: 1, country: '미국', reason: '북미 사건의 86% 차지, 264개 위협 행위자 타운', icon: '🇺🇸' },
      { rank: 2, country: '우크라이나', reason: '2024년 2,052건(지정학적 긴장/전쟁 관련)', icon: '🇺🇦' },
      { rank: 3, country: '이스라엘', reason: '2024년 1,550건(중동 분쟁 관련 공격 집중)', icon: '🇮🇱' },
      { rank: 4, country: '일본', reason: '아태지역 공격의 66%, 제조업·금융 타겟', icon: '🇯🇵' },
      { rank: 5, country: '영국', reason: '유럽 내 말웨어 공격 3위, 1억 건 이상 시도', icon: '🇬🇧' },
      { rank: 6, country: '사우디', reason: '중동 공격의 63%, 석유·에너지 인프라 집중', icon: '🇸🇦' },
      { rank: 7, country: '브라질', reason: '라틴아메리카 53%, 뱅킹·공공 부문 타겟', icon: '🇧🇷' },
      { rank: 8, country: '인도', reason: '말웨어 비중 12.4%, 급성장 핀테크 부문 표적', icon: '🇮🇳' },
      { rank: 9, country: '독일', reason: '유럽 공격의 18%, 고도화된 산업 스파이 위협', icon: '🇩🇪' },
      { rank: 10, country: '폴란드', reason: 'EU 내 러시아 발 사이버 공격 최다 발생', icon: '🇵🇱' },
    ],

    // 랜섬웨어 통계 (2024-2025)
    ransomwareStats: {
      regional: {
        labels: ['북미', '유럽', '아태', '기타'],
        data: [57, 24, 13, 6]
      },
      industry: {
        labels: ['제조업', '의료', '기타'],
        data: [30, 13, 57]
      }
    },

    // 글로벌 위협 주요 지표 3개년 추이 (2022-2024)
    globalDetailedTrends: {
      years: [2022, 2023, 2024],
      costPerSec: [222, 267, 302],      // 초당 손실액 (k$)
      attackInterval: [44, 41, 39],     // 공격 발생 간격 (초)
      weeklyAttacks: [1168, 1258, 1636], // 기업당 주간 평균 공격 (건)
    },

    // 대륙별 시장 비중 (2024 실적, %)
    regionalShare: {
      labels: ['북미', '유럽', '아태 (APAC)', '중동/아프리카'],
      data: [43.1, 25.4, 21.8, 9.7],
    },

    // 대륙별 성장률 (CAGR 24-26, %)
    regionalCAGR: {
      labels: ['북미', '유럽', '아태 (APAC)', '중동/아프리카'],
      data: [11.5, 10.8, 15.4, 12.2],
    },

    // 랜섬웨어 산업별 비중 (Check Point Q2 2024)
    ransomwareIndustryShare: [
      { rank: 1, industry: '제조업', share: '29%', change: '+56%', reason: '공급망 취약점 노출' },
      { rank: 2, industry: '의료·헬스케어', share: '11%', change: '+27%', reason: '환자 데이터 인질화' },
      { rank: 3, industry: '소매·도매', share: '9%', change: '-34%', reason: '보안 강화로 인한 감소' },
      { rank: 4, industry: '금융·은행', share: '7%', change: '-8%', reason: '고도화된 방어 체계' },
      { rank: 5, industry: '교육·연구', share: '6%', change: '-3%', reason: '상시적 위협 노출' },
      { rank: 6, industry: '정부·군사', share: '6%', change: '+31%', reason: '국가 배후 공격 증가' },
      { rank: 7, industry: '운송·물류', share: '6%', change: '+40%', reason: '물류 허브 중단 노이즈' },
      { rank: 8, industry: '통신', share: '5%', change: '+177%', reason: '인프라 마비 시도 급증' },
    ],

    // 랜섬웨어 산업별 공격 건수 (Comparitech 2025)
    ransomwareIndustryCount: [
      { rank: 1, industry: '제조업', count: '1,466건', change: '+56%', note: '평균 몸값 $1.16M' },
      { rank: 2, industry: '헬스케어', count: '444건', change: '+2%', note: '생명 직결 시스템 타겟' },
      { rank: 3, industry: '정부기관', count: '374건', change: '+27%', note: '공능 서비스 중단 시도' },
      { rank: 4, industry: '법률·보험', count: '346건', change: '+54%', note: '민감 정보 유출 목적' },
      { rank: 5, industry: '교육기관', count: '252건', change: '유지', note: '랜섬웨어 상시 타겟' },
    ],

    // 국내 산업별 위협 순위 (2025 상반기)
    // 출처: ISAC / SKShieldus 종합
    domesticIndustryStats2025: [
      { rank: 1, industry: '정보통신업', feature: '신고 비중 1위, 클라우드/API 타겟 증가' },
      { rank: 2, industry: '제조업·공공', feature: '비중 18%, 공급망 및 국가 기간망 공격' },
      { rank: 3, industry: '금융·교육', feature: '비중 15%, 피싱 및 데이터 탈취 집중' },
      { rank: 4, industry: 'IT·의료·도소매', feature: '비중 8%, 랜섬웨어 및 결제 시스템 위협' },
    ],

    // 주요 국가별 상세 통계
    countryStats: [
      { country: '미국', tier: 'Tier 1', market: '$102.4B', strategy: 'CISA Strategic Plan 2026', url: 'https://www.cisa.gov/strategy' },
      { country: '영국', tier: 'Tier 1', market: '$19.5B', strategy: 'UK NCSC Annual Review 2025', url: 'https://www.ncsc.gov.uk/reports' },
      { country: '일본', tier: 'Tier 1', market: '$14.2B', strategy: 'NISC Japan 2026 Outlook', url: 'https://www.nisc.go.jp/en/' },
      { country: '호주', tier: 'Tier 1', market: '$9.8B', strategy: 'ASCSC Annual Report 2026', url: 'https://www.cyber.gov.au/reports' },
      { country: '독일', tier: 'Tier 1', market: '$13.1B', strategy: 'BSI State of IT Security 2026', url: 'https://www.bsi.bund.de/EN/' },
      { country: '프랑스', tier: 'Tier 1', market: '$11.4B', strategy: 'ANSSI Activity Report 2026', url: 'https://cyber.gouv.fr/en/' },
      { country: '중국', tier: 'Tier 1', market: '$18.9B', strategy: 'CNNIC 54th Report', url: 'https://www.cnnic.com.cn/IDR/' },
      { country: '러시아', tier: 'Tier 2', market: '$5.8B', strategy: 'TAdviser Cyber Market', url: 'https://www.tadviser.ru' },
    ],

    // 글로벌 하이라이트 수치 (최신 업데이트 - 일반 사이버 위협 지표)
    globalHighlights: [
      { num: '1,636건', color: '#f87171', label: '주당 평균 공격 (기업당, 24 Q2)' },
      { num: '39초',     color: '#f59e0b', label: '공격 발생 간격 (전 세계 평균)' },
      { num: '$2,088억', color: '#60a5fa', label: '글로벌 보안 시장 (24 실적)' },
      { num: '$9.5조',   color: '#34d399', label: '사이버 범죄 비용 (24 추산)' },
    ],

    // 글로벌 인사이트 10대 지표 (Bento Grid 용)
    top10Insights: [
      { id: 1,  title: '사이버 범죄 총 비용',     value: '$10.5T',  sub: '2025년 전망 (연 15% 성장)', icon: 'fa-money-bill-wave', color: '#f87171', source: 'Bluefire Redteam', url: 'https://bluefire-redteam.com/top-50-cybersecurity-statistics-for-2025/' },
      { id: 2,  title: '데이터 유출 평균 비용',   value: '$4.44M',  sub: '2025년 기업당 평균', icon: 'fa-user-shield', color: '#fb923c', source: 'IBM/Bluefire', url: 'https://bluefire-redteam.com/top-50-cybersecurity-statistics-for-2025/' },
      { id: 3,  title: '보안 시장 규모',         value: '$2,130억', sub: '2025년 전 세계 시장 (+10%)', icon: 'fa-chart-line', color: '#60a5fa', source: 'Cobalt', url: 'https://bluefire-redteam.com/top-50-cybersecurity-statistics-for-2025/' },
      { id: 4,  title: '취약점 공개 건수',       value: '30,000+', sub: '2025년 신규 CVE (17%↑)', icon: 'fa-bug', color: '#a78bfa', source: 'SentinelOne', url: 'https://www.sentinelone.com/ko/cybersecurity-101/cybersecurity/cyber-security-trends/' },
      { id: 5,  title: '랜섬웨어 복구 비용',     value: '$273만',  sub: '평균 복구 및 대응 비용', icon: 'fa-tools', color: '#34d399', source: 'SentinelOne', url: 'https://www.sentinelone.com/ko/cybersecurity-101/cybersecurity/cyber-security-trends/' },
      { id: 6,  title: 'AI 취약점 우려',         value: '87%',     sub: '조직 87%가 주요 위험으로 지목', icon: 'fa-robot', color: '#22d3ee', source: 'ECCU', url: 'https://www.eccu.edu/blog/top-cybersecurity-threats-2026/' },
      { id: 7,  title: '피싱 기인 침해 비율',     value: '91%',     sub: '성공한 침해의 91%가 피싱 기반', icon: 'fa-hook', color: '#f472b6', source: 'ECCU', url: 'https://www.eccu.edu/blog/top-cybersecurity-threats-2026/' },
      { id: 8,  title: '침해 중 랜섬웨어 비중',   value: '44%',     sub: '2025년 전체 사고 중 비중 (32%↑)', icon: 'fa-biohazard', color: '#fbbf24', source: 'DataPatrol', url: 'https://datapatrol.com/10-cybersecurity-statistics-every-business-should-know-in-2025/' },
      { id: 9,  title: '클라우드 침투 증가',     value: '136%',    sub: '2025년 상반기 전년 대비 증가율', icon: 'fa-cloud-upload-alt', color: '#818cf8', source: 'ABI Research', url: 'https://www.abiresearch.com/blog/top-cybersecurity-trends' },
      { id: 10, title: '국내 침해사고 신고',     value: '2,383건', sub: '2025년 KISA 신고 건수 (+26.3%)', icon: 'fa-shield-alt', color: '#4ade80', source: 'KDI/KISA', url: 'https://eiec.kdi.re.kr/policy/callDownload.do?num=276297&filenum=1&dtime=20260127164853' },
    ],

    // ── AI 분야 탭 ─────────────────────────────────────────
    
    // AI 하이라이트 수치
    aiHighlights: [
      { num: '16%',      color: '#f87171', label: 'AI 연계 침해 비중 (2025)' },
      { num: '72%↑',    color: '#f87171', label: 'AI 지원 공격 증가율' },
      { num: '1,265%↑', color: '#f59e0b', label: 'AI 피싱 증가 (22년비)' },
      { num: '$1,346억', color: '#60a5fa', label: 'AI 보안 시장 (2030E)' },
    ],

    // AI 보안 시장 성장 전망 ($B)
    aiMarketGrowth: {
      years: [2024, 2025, 2026, 2027, 2028, 2029, 2030],
      values: [310, 410, 520, 680, 860, 1080, 1346],
      estimateFrom: 1,
    },

    // AI 악용 공격 성공률 및 위협 지표 (%)
    aiSuccessRates: {
      labels: ['음성사기 성공률', '딥페이크 비중', 'BEC 증가율', '공격 건수 증가', '프롬프트 인젝션'],
      data: [77, 6.5, 37, 47, 3.3],
    },

    // AI 위협 주요 지표 3개년 추이
    aiAttackTrends: {
      years: [2023, 2024, 2025],
      attackCounts: [9, 16.3, 28], // 백만 건
      aiShare: [5, 10, 16],       // 전체 침해 중 비중 (%)
      phishingGrowth: [200, 600, 1265], // 22년 대비 누적 증가율 (%)
    },

    // 산업별 AI 리스크 인사이트
    aiIndustryInsights: [
      { industry: '금융', threat: 'AI 생성 피싱 및 맞춤화 사기', detail: '피싱 이메일 개봉률 78%, 링크 클릭률 21% 기록 (전통 방식 대비 압도적 높음)' },
      { industry: '헬스케어', threat: '훈련 데이터 유출 및 모델 공격', detail: '의료 AI 모델 훈련용 민감 데이터 저장소 수백 개 노출 사례 보고 (Trend Micro)' },
      { industry: '제조업', threat: 'AI 공급망 및 랜섬웨어 결합', detail: '제조 부문 랜섬웨어 공격 32% 증가, AI 기반 공급망 취약점 탐색 가속화' },
      { industry: '공공·클라우드', threat: 'AI 서비스 및 인프라 타겟 공격', detail: '2025년 하반기 기준 AI 서비스 직접 타겟 공격 36.5% 급증 (과기정통부)' },
      { industry: '기업 공통', threat: '내부 GenAI 오용 및 권한 관리', detail: '기업 13%가 AI 보안 사고 경험, 이 중 97%가 접근 제어 미비가 원인' },
    ],

  }, // end charts

}; // end DASHBOARD_DATA
