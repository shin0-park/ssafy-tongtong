export const LIBRARY_TYPE_LABELS = {
  public: '공공도서관',
  small: '작은도서관',
  children: '어린이도서관',
  other: '도서관',
}

export const PURPOSE_LABELS = {
  study: '공부하기 좋은 곳',
  book: '책 보기 좋은 곳',
  kids: '아이와 가기 좋은 곳',
  mood: '분위기 좋은 곳',
  nearby: '가까운 곳',
}

export const PURPOSE_SHORT_LABELS = {
  study: '공부형',
  book: '책 탐색형',
  program: '프로그램형',
  rest: '휴식형',
}

export const FACILITY_LABELS = {
  has_reading_room: '열람실',
  has_children_room: '어린이자료실',
  has_digital_room: '디지털자료실',
  has_parking: '주차장',
  has_cafe: '카페',
  has_wifi: '와이파이',
  has_nursing_room: '수유실',
  has_accessible_facility: '장애인 편의시설',
  has_elevator: '엘리베이터',
  has_lounge: '휴게공간',
  has_outdoor_space: '야외공간',
}

export const PROGRAM_CATEGORY_LABELS = {
  lecture_humanities: '강연/인문',
  reading_writing: '독서/글쓰기',
  culture_art: '문화/예술',
  experience_education: '체험/교육',
  exhibition: '전시',
  other: '기타',
}

export const PROGRAM_TARGET_LABELS = {
  for_infant: '유아',
  for_elementary: '초등',
  for_teen: '청소년',
  for_adult: '성인',
  for_senior: '시니어',
  for_family: '가족',
  all: '전체',
}

export const APPLICATION_STATUS_LABELS = {
  available: '신청 가능',
  closed: '신청 마감',
  not_required: '신청 없음',
}

export const OPERATION_STATUS_LABELS = {
  upcoming: '예정',
  ongoing: '진행 중',
  ended: '종료',
}

export const REVIEW_TAG_LABELS = {
  study_reading: '공부/열람',
  space_atmosphere: '공간/분위기',
  collection: '책/자료',
  program: '프로그램',
  kids_family: '아이/가족',
  access_convenience: '접근/편의',
  guidance_management: '안내/관리',
  review_quiet_study: '조용한 공부 환경',
  review_seats_sufficient: '충분한 좌석',
  review_comfortable_reading_space: '쾌적한 열람공간',
  review_comfortable_space: '편안한 공간',
  review_clean_space: '깔끔하고 쾌적해요',
  review_books_diverse: '책이 다양해요',
  review_easy_book_finding: '책 찾기가 편해요',
  review_good_programs: '프로그램이 좋아요',
  review_children_friendly: '아이와 가기 좋아요',
  review_parking_convenient: '주차가 편해요',
  review_wifi_reliable: '와이파이가 잘 돼요',
  review_kind_guidance: '안내가 친절해요',
  review_well_managed: '관리가 잘 되어 있어요',
}

export function labelFromMap(map, value, fallback = '정보 없음') {
  return map[value] || value || fallback
}

export function isBrokenText(value) {
  return typeof value === 'string' && /[�]|[?][\u3131-\uD79D]|[泥섎━]/.test(value)
}

export function formatDate(value, fallback = '정보 없음') {
  if (!value) return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

export function formatNumber(value, fallback = '-') {
  if (value === null || value === undefined || value === '') return fallback
  const number = Number(value)
  return Number.isFinite(number) ? number.toLocaleString('ko-KR') : fallback
}

export function normalizeList(value) {
  if (!value) return []
  if (Array.isArray(value)) return value
  return String(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}
