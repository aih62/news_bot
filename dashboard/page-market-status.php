<?php
/**
 * Template Name: Dashboard - Market Status
 * 
 * 정보보호 통계 대시보드 전용 페이지 템플릿
 */

get_header(); ?>

<div id="primary" class="content-area">
    <main id="main" class="site-main">

        <!-- 정보보호 통계 대시보드 - CSS/JS 연결 -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>

        <?php
        $assets_url = get_site_url() . '/wp-content/uploads/dashboard';
        ?>
        <link rel="stylesheet" href="<?php echo $assets_url; ?>/dashboard.css?v=20260322_1500">

        <div id="db-dashboard-root">
            <!-- 헤더 -->
            <div class="db-header">
                <div class="db-title">사이버보안 대시보드</div>
            </div>

            <!-- 네비게이션 -->
            <div class="db-nav-wrapper">
                <!-- 1단계: 메인 카테고리 -->
                <div class="db-main-nav">
                    <button class="db-main-tab active" data-main="overview">📊 종합 현황</button>
                    <button class="db-main-tab" data-main="global">🌍 글로벌 현황</button>
                </div>

                <!-- 2단계: 서브 카테고리 (종합 현황) -->
                <div class="db-sub-nav-group active" id="db-sub-overview">
                    <button class="db-tab active" data-section="overview">🏠 개요</button>
                    <button class="db-tab" data-section="industry">🏭 산업</button>
                    <button class="db-tab" data-section="incidents">💥 침해</button>
                    <button class="db-tab" data-section="talent">👨‍💻 인력</button>
                    <button class="db-tab" data-section="cert">📜 인증</button>
                    <button class="db-tab" data-section="prevention">🛡️ 예방</button>
                </div>

                <!-- 2단계: 서브 카테고리 (글로벌 현황) -->
                <div class="db-sub-nav-group" id="db-sub-global">
                    <button class="db-tab" data-section="global-economy">📉 경제/추이</button>
                    <button class="db-tab" data-section="global-threat">🎯 공격/위협</button>
                    <button class="db-tab" data-section="global-ai">🤖 AI 분야</button>
                    <button class="db-tab" data-section="global-deep">🔍 심층 분석</button>
                    <button class="db-tab" data-section="global-insights"><i class="fas fa-lightbulb"></i> 인사이트</button>
                </div>
            </div>

            <!-- ===== [종합] 개요 ===== -->
            <div id="db-section-overview" class="db-section active">
                <div class="db-kpi-grid" id="db-kpi-container"></div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">정보보호 산업 매출액 추이</div>
                        <div class="db-chart-subtitle">단위: 억원 · 2020–2024</div>
                        <div class="db-chart-wrap"><canvas id="db-c-revenue"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">침해사고 신고접수 추이</div>
                        <div class="db-chart-subtitle">단위: 건 · 2022–2025</div>
                        <div class="db-chart-wrap"><canvas id="db-c-incidents"></canvas></div>
                    </div>
                </div>
                <div class="db-chart-grid three">
                    <div class="db-chart-card">
                        <div class="db-chart-title">2024년 매출 비중</div>
                        <div class="db-chart-subtitle">정보보안 vs 물리보안</div>
                        <div class="db-chart-wrap"><canvas id="db-c-share"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">2026년 2월 침해신고 유형</div>
                        <div class="db-chart-subtitle">415건 기준</div>
                        <div class="db-chart-wrap"><canvas id="db-c-incident-share"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">글로벌 랜섬웨어 피해 규모</div>
                        <div class="db-chart-subtitle">단위: 억 달러 · Cybersecurity Ventures</div>
                        <div class="db-chart-wrap"><canvas id="db-c-ransomware"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [종합] 산업 ===== -->
            <div id="db-section-industry" class="db-section">
                <div class="db-info-block">
                    <strong>2024년 정보보호 산업 총매출 18.6조원</strong> (전년 대비 +10.5%) |
                    정보보안 기업 876개, 물리보안 904개, 총 <strong>1,780개</strong> 기업 활동 중
                </div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">연도별 정보보호 산업 매출액</div>
                        <div class="db-chart-subtitle">정보보안 + 물리보안 합계 (억원)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-rev2"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">연도별 정보보호 수출액</div>
                        <div class="db-chart-subtitle">단위: 억원</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-export"></canvas></div>
                    </div>
                </div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">정보보호 기업 수 추이</div>
                        <div class="db-chart-subtitle">단위: 개 · CAGR 5년 8.5%</div>
                        <div class="db-chart-wrap"><canvas id="db-c-companies"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">연도별 정보통신업 신고접수 현황</div>
                        <div class="db-chart-subtitle">단위: 건 (국내 통계)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-it-incidents"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [종합] 침해 ===== -->
            <div id="db-section-incidents" class="db-section">
                <h3 class="db-sub-title"><i class="fas fa-exclamation-triangle"></i> 최근 침해사고 주요 지표</h3>
                <div class="db-highlight-grid" id="db-highlights-incidents"></div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">분기별 침해신고 접수 현황</div>
                        <div class="db-chart-subtitle">2022 Q1 – 2025 Q4 (건)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-quarterly-incidents"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">월별 침해사고 신고 추이</div>
                        <div class="db-chart-subtitle">최근 12개월 (건)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-monthly-incidents"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [종합] 인력 ===== -->
            <div id="db-section-talent" class="db-section">
                <div class="db-info-block">
                    <strong>사이버 10만 인재 양성 목표 달성!</strong>
                    2026년 2월 말 기준 누적 <strong>104,032명</strong> 양성 (2022~2026, 목표 초과 달성)
                </div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">정보보호 산업 인력 추이</div>
                        <div class="db-chart-subtitle">단위: 명</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-workforce"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">사이버 10만 인재 양성 누적 실적</div>
                        <div class="db-chart-subtitle">2022~2026 누적 (명)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-talent"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [종합] 인증 ===== -->
            <div id="db-section-cert" class="db-section">
                <h3 class="db-sub-title"><i class="fas fa-certificate"></i> ISMS / ISMS-P 인증 현황</h3>
                <div class="db-highlight-grid" id="db-highlights-cert"></div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">ISMS 인증 건수 추이</div>
                        <div class="db-chart-subtitle">정보보호 관리체계 인증</div>
                        <div class="db-chart-wrap"><canvas id="db-c-isms"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">클라우드 보안인증 추이</div>
                        <div class="db-chart-subtitle">IaaS / SaaS / DaaS</div>
                        <div class="db-chart-wrap"><canvas id="db-c-cloud"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [종합] 예방 ===== -->
            <div id="db-section-prevention" class="db-section">
                <h3 class="db-sub-title"><i class="fas fa-user-shield"></i> 정보보호 예방 및 투자 지표</h3>
                <div class="db-highlight-grid" id="db-highlights-prevent"></div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">C-TAS 참여기업 및 공유건수 추이</div>
                        <div class="db-chart-subtitle">사이버위협 정보공유시스템</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-ctas"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">사이버위기 대응 모의훈련</div>
                        <div class="db-chart-subtitle">참여기업 및 인원 추이</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-drill"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [글로벌] 경제/추이 ===== -->
            <div id="db-section-global-economy" class="db-section">
                <div class="db-highlight-grid" id="db-highlights-global" style="margin-bottom:24px"></div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">글로벌 사이버보안 지표 추이 (2023–2026)</div>
                        <div class="db-chart-subtitle">시장규모($B) vs AI 기반 공격탐지(%) · WEF 2026</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-global-market-cost"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">전 세계 사이버 범죄 비용 전망(2015–2030)</div>
                        <div class="db-chart-subtitle">단위: $T (Trillion) · Cybersecurity Ventures</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-cybercrime-cost"></canvas></div>
                    </div>
                </div>
                <h3 class="db-sub-title"><i class="fas fa-history"></i> 위협 메트릭 3개년 추이 분석</h3>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">초당 사이버 범죄 피해액 추이 (2022–2024)</div>
                        <div class="db-chart-subtitle">단위: k$ (천 달러)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-trend-cost-sec"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">공격 빈도 및 발생 간격 추이 (2022–2024)</div>
                        <div class="db-chart-subtitle">주간 공격(건) vs 공격 간격(초)</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-trend-frequency"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [글로벌] 공격/위협 ===== -->
            <div id="db-section-global-threat" class="db-section">
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">지역별 기업당 주간 평균 공격 수 (2024 Q3)</div>
                        <div class="db-chart-subtitle">출처: Check Point Research</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-attacks-region"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">산업별 기업당 주간 평균 공격 수 (2024 Q2)</div>
                        <div class="db-chart-subtitle">출처: Check Point Research</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-attacks-industry"></canvas></div>
                    </div>
                </div>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">대륙별 시장 비중 (2024 실적)</div>
                        <div class="db-chart-wrap"><canvas id="db-c-regional-share"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">대륙별 시장 성장률 (CAGR 24-26)</div>
                        <div class="db-chart-wrap"><canvas id="db-c-regional-cagr"></canvas></div>
                    </div>
                </div>
            </div>

            <!-- ===== [글로벌] 심층 분석 ===== -->
            <div id="db-section-global-deep" class="db-section">
                <h3 class="db-sub-title"><i class="fas fa-bullseye"></i> 2025 국가별 사이버 공격 타겟 순위</h3>
                <div class="db-chart-card">
                    <div class="db-table-scroll">
                        <table class="db-data-table">
                            <thead>
                                <tr>
                                    <th style="width:60px">순위</th>
                                    <th style="width:120px">대상 국가</th>
                                    <th>주요 공격 원인 및 지표</th>
                                </tr>
                            </thead>
                            <tbody id="db-c-table-targeted"></tbody>
                        </table>
                    </div>
                </div>

                <h3 class="db-sub-title"><i class="fas fa-industry"></i> 산업별 사이버 위협 심층 분석</h3>
                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">글로벌 랜섬웨어 산업별 비중 (24 Q2)</div>
                        <div class="db-table-scroll">
                            <table class="db-data-table">
                                <thead>
                                    <tr>
                                        <th>순위</th>
                                        <th>산업분야</th>
                                        <th>비중</th>
                                        <th>증감</th>
                                        <th>특징</th>
                                    </tr>
                                </thead>
                                <tbody id="db-c-table-industry-share"></tbody>
                            </table>
                        </div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">글로벌 랜섬웨어 산업별 공격 건수 (25E)</div>
                        <div class="db-table-scroll">
                            <table class="db-data-table">
                                <thead>
                                    <tr>
                                        <th>순위</th>
                                        <th>산업분야</th>
                                        <th>공격건수</th>
                                        <th>증감</th>
                                        <th>비고</th>
                                    </tr>
                                </thead>
                                <tbody id="db-c-table-industry-count"></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <h3 class="db-sub-title"><i class="fas fa-flag"></i> 국내(한국) 산업별 위협 순위 (2025 상반기)</h3>
                <div class="db-chart-card" style="margin-bottom:24px">
                    <div class="db-table-scroll">
                        <table class="db-data-table">
                            <thead>
                                <tr>
                                    <th style="width:60px">순위</th>
                                    <th style="width:150px">산업분야</th>
                                    <th>주요 위협 특징</th>
                                </tr>
                            </thead>
                            <tbody id="db-c-table-industry-domestic"></tbody>
                        </table>
                    </div>
                </div>

                <h3 class="db-sub-title"><i class="fas fa-globe"></i> 주요 국가별 상세 지표 (2024-2026)</h3>
                <div class="db-chart-card">
                    <div class="db-table-scroll">
                        <table class="db-data-table">
                            <thead>
                                <tr>
                                    <th>국가</th>
                                    <th>티어</th>
                                    <th>보안시장($B)</th>
                                    <th>국가 사이버 전략 및 보고서</th>
                                </tr>
                            </thead>
                            <tbody id="db-table-countries"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- ===== [글로벌] AI 분야 ===== -->
            <div id="db-section-global-ai" class="db-section">
                <div class="db-info-block">
                    <strong>AI 기반 사이버 위협의 부상:</strong> 2025년 기준 글로벌 침해 사고의 약 <strong>16%</strong>가 AI 연계 위협으로 분류되며, 
                    공격 자동화와 AI 시스템 자체를 노리는 표적 공격이 급증하고 있습니다.
                </div>
                
                <div class="db-highlight-grid" id="db-highlights-ai" style="margin-bottom:24px"></div>

                <div class="db-chart-grid two">
                    <div class="db-chart-card">
                        <div class="db-chart-title">AI 보안 시장 성장 전망 (2024–2030)</div>
                        <div class="db-chart-subtitle">단위: $B (Billion) · CAGR 26.6%</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-ai-market-growth"></canvas></div>
                    </div>
                    <div class="db-chart-card">
                        <div class="db-chart-title">AI 악용 공격 성공률 및 위협 지표</div>
                        <div class="db-chart-subtitle">음성사기(77%), 피싱증가(1,265%) 등 주요 지표</div>
                        <div class="db-chart-wrap tall"><canvas id="db-c-ai-success-rates"></canvas></div>
                    </div>
                </div>

                <h3 class="db-sub-title"><i class="fas fa-chart-line"></i> AI 위협 주요 지표 3개년 추이 (2023–2025)</h3>
                <div class="db-chart-card" style="margin-bottom:24px">
                    <div class="db-chart-title">AI 관련 공격 건수 및 전체 비중 변화</div>
                    <div class="db-chart-subtitle">전 세계 추정치 기준</div>
                    <div class="db-chart-wrap" style="height:350px"><canvas id="db-c-ai-attack-trends"></canvas></div>
                </div>

                <h3 class="db-sub-title"><i class="fas fa-building"></i> 산업별 AI 리스크 및 대응 인사이트</h3>
                <div class="db-chart-card">
                    <div class="db-table-scroll">
                        <table class="db-data-table">
                            <thead>
                                <tr>
                                    <th style="width:120px">산업분야</th>
                                    <th style="width:250px">주요 AI 위협 및 특징</th>
                                    <th>상세 데이터 및 인용 지표</th>
                                </tr>
                            </thead>
                            <tbody id="db-c-table-ai-industry"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- ===== [글로벌] 인사이트 ===== -->
            <div id="db-section-global-insights" class="db-section">
                <h3 class="db-sub-title"><i class="fas fa-bolt"></i> 사이버보안 10대 핵심 지표 (2025-2026)</h3>
                <div id="db-insights-grid" class="db-insight-grid">
                    <!-- JS로 렌더링 -->
                </div>
            </div>
        </div><!-- /#db-dashboard-root -->

        <script src="<?php echo $assets_url; ?>/dashboard-data.js?v=20260322_1500"></script>
        <script src="<?php echo $assets_url; ?>/dashboard-render.js?v=20260322_1500"></script>

    </main>
</div>

<?php get_footer(); ?>
