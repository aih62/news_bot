<?php
/**
 * 파일명: set-external-image.php
 * 역할: 외부 이미지 URL을 워드프레스 포스트의 특성 이미지로 강제 연결
 */

// 1. 보안 설정
$secret_token = 'ajken_secure_2024_auth';
if (!isset($_GET['token']) || $_GET['token'] !== $secret_token) {
    header('HTTP/1.1 403 Forbidden');
    die('AUTH_FAILED');
}

// 2. 워드프레스 환경 로드
require_once('wp-load.php');

// 3. 데이터 수신
$post_id = isset($_POST['post_id']) ? intval($_POST['post_id']) : 0;
$image_url = isset($_POST['image_url']) ? $_POST['image_url'] : '';

if ($post_id > 0 && !empty($image_url)) {
    // 4. 메타 데이터 업데이트 (공개/비공개 키 모두)
    update_post_meta($post_id, 'fifu_image_url', $image_url);
    update_post_meta($post_id, '_fifu_image_url', $image_url);
    
    // 5. FIFU 플러그인 전용 함수 호출 (설치되어 있다면)
    if (function_exists('fifu_dev_set_image')) {
        fifu_dev_set_image($post_id, $image_url);
        echo "SUCCESS_WITH_FIFU";
    } else {
        echo "SUCCESS_META_ONLY";
    }
} else {
    echo "INVALID_PARAMS";
}
?>
