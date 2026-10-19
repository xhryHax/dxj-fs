<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as fileLogicApi from '../api/fileLogic'
import * as fileIoApi from '../api/fileIo'
import { downloadByUrl } from '../utils/download'
import Card from '../components/ui/Card.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import FileList from '../components/business/FileList.vue'

const router = useRouter()

const pages = ref([])
const current = ref(null)
const files = ref([])
const loading = ref(true)
const filesLoading = ref(false)

onMounted(() => load().catch(() => {}))

async function load() {
  loading.value = true
  try {
    pages.value = await fileLogicApi.getPublicPages()
    if (pages.value.length) selectPage(pages.value[0])
  } finally {
    loading.value = false
  }
}

async function selectPage(page) {
  current.value = page
  filesLoading.value = true
  try {
    const res = await fileLogicApi.getPublicPageFiles(page.groupId)
    files.value = res.info || []
  } finally {
    filesLoading.value = false
  }
}

async function handleDownload(file) {
  const { fileURL, fileName } = await fileIoApi.getDownloadLink(current.value.groupId, file.fileId)
  downloadByUrl(fileURL, fileName)
}
</script>

<template>
  <div class="page">
    <header class="head">
      <button class="back-link" @click="router.push('/profile')">← 个人中心</button>
      <h2>访问公开页</h2>
      <p class="muted">所有组发布的公开页面，点击查看公告与文件。</p>
    </header>

    <Spinner v-if="loading" class="loading" :size="32" />

    <template v-else-if="pages.length">
      <div class="page-tabs">
        <button
          v-for="p in pages"
          :key="p.publicPageId"
          class="page-tab"
          :class="{ 'page-tab--active': current?.publicPageId === p.publicPageId }"
          @click="selectPage(p)"
        >
          <span class="tab-name">{{ p.groupName }}</span>
        </button>
      </div>

      <Card v-if="current" class="detail">
        <h3 class="detail-title">{{ current.groupName }} · 公开页</h3>
        <div class="announcement">
          <p class="announcement-text">{{ current.announcement || '暂无公告' }}</p>
        </div>

        <h4 class="section-title">页面文件</h4>
        <Spinner v-if="filesLoading" class="loading" :size="24" />
        <FileList v-else :files="files" @download="handleDownload" />
      </Card>
    </template>

    <EmptyState v-else message="暂无公开页" hint="目前没有任何组发布公开页面" />
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 24px;
}
.back-link {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 19px;
}
.back-link:hover {
  color: var(--text-primary);
}
.loading {
  display: block;
  margin: 64px auto;
}
.page-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.page-tab {
  padding: 8px 16px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 19px;
  font-weight: 600;
  transition: box-shadow 0.15s ease;
}
.page-tab:hover {
  box-shadow: var(--shadow-focus);
}
.page-tab--active {
  background: var(--text-primary);
  color: var(--text-on-dark);
  border-color: var(--text-primary);
}
.detail-title {
  margin-bottom: 12px;
}
.announcement {
  background: rgba(28, 28, 28, 0.04);
  border-left: 3px solid var(--border-interactive);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin-bottom: 24px;
}
.announcement-text {
  margin: 0;
  white-space: pre-wrap;
}
.section-title {
  margin-bottom: 12px;
}
</style>
