<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  latitude: {
    type: [Number, String],
    default: null,
  },
  longitude: {
    type: [Number, String],
    default: null,
  },
  title: {
    type: String,
    default: '도서관 위치',
  },
  address: {
    type: String,
    default: '',
  },
})

const mapElement = ref(null)
const status = ref('idle')
const errorMessage = ref('')

const kakaoJavascriptKey = import.meta.env.VITE_KAKAO_MAP_JAVASCRIPT_KEY
const lat = computed(() => Number(props.latitude))
const lng = computed(() => Number(props.longitude))
const hasCoordinates = computed(() => Number.isFinite(lat.value) && Number.isFinite(lng.value))
const externalMapUrl = computed(() => {
  const query = encodeURIComponent(props.address || props.title)
  return `https://map.kakao.com/link/search/${query}`
})

function loadKakaoSdk() {
  if (!kakaoJavascriptKey) {
    return Promise.reject(new Error('Kakao JavaScript key is missing.'))
  }

  if (window.kakao?.maps) {
    return Promise.resolve(window.kakao)
  }

  return new Promise((resolve, reject) => {
    const existingScript = document.getElementById('kakao-map-sdk')

    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.kakao), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Kakao map SDK load failed.')), {
        once: true,
      })
      return
    }

    const script = document.createElement('script')
    script.id = 'kakao-map-sdk'
    script.async = true
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoJavascriptKey}&autoload=false`
    script.onload = () => resolve(window.kakao)
    script.onerror = () => reject(new Error('Kakao map SDK load failed.'))
    document.head.append(script)
  })
}

async function renderMap() {
  errorMessage.value = ''

  if (!hasCoordinates.value) {
    status.value = 'fallback'
    errorMessage.value = '좌표 정보가 없어 주소로 위치를 확인할 수 있어요.'
    return
  }

  if (!mapElement.value) {
    return
  }

  status.value = 'loading'

  try {
    const kakao = await loadKakaoSdk()
    kakao.maps.load(() => {
      const center = new kakao.maps.LatLng(lat.value, lng.value)
      const map = new kakao.maps.Map(mapElement.value, {
        center,
        level: 4,
      })

      new kakao.maps.Marker({
        map,
        position: center,
        title: props.title,
      })

      status.value = 'ready'
    })
  } catch {
    status.value = 'fallback'
    errorMessage.value = kakaoJavascriptKey
      ? '지도를 불러오지 못했어요. 주소로 위치를 확인해주세요.'
      : '지도 설정이 없어 주소로 위치를 확인해주세요.'
  }
}

watch(() => [props.latitude, props.longitude], renderMap)
onMounted(renderMap)
</script>

<template>
  <section class="content-panel p-4">
    <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
      <h2 class="section-title mb-0">위치</h2>
      <a class="btn btn-outline-primary btn-sm" :href="externalMapUrl" target="_blank" rel="noopener noreferrer">
        외부 지도
      </a>
    </div>

    <div v-show="status === 'ready' || status === 'loading'" ref="mapElement" class="kakao-map-panel">
      <span v-if="status === 'loading'" class="meta-text">지도를 불러오는 중입니다.</span>
    </div>

    <div v-if="status === 'fallback'" class="map-fallback">
      <p class="meta-text mb-2">{{ errorMessage }}</p>
      <p class="mb-0">{{ address || '주소 정보 없음' }}</p>
    </div>
  </section>
</template>
