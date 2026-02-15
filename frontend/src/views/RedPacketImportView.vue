<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  batchImportRedPacketUrls,
  createRedPacket,
  createRedPacketCategory,
  listRedPacketCategories,
  parseImagesToUrls,
  type ParsedImageUrlItem,
  type RedPacketCategory,
} from '../api/modules/redPacket'

const CUSTOM_CATEGORY_VALUE = '__custom__'

const router = useRouter()
const loading = shallowRef(false)
const message = shallowRef('')
const categories = shallowRef<RedPacketCategory[]>([])
const showCustomCategoryInput = shallowRef(false)
const categorySelectValue = shallowRef('alipay_red_packet')
const categoryMenuOpen = shallowRef(false)
const categoryMenuRef = ref<HTMLElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const imageFiles = shallowRef<File[]>([])
const parsing = shallowRef(false)
const parsedImageResults = shallowRef<ParsedImageUrlItem[]>([])

const form = reactive({
  title: '支付宝红包',
  amount: 0,
  level: 1,
  category_code: 'alipay_red_packet',
  custom_category_name: '',
  content_type: 'qr_image' as 'url' | 'text' | 'qr_image',
  content_value: '',
  tags_text: '',
  available_from: '',
  available_to: '',
  red_packet_created_at: '',
  account_provider: 'Google',
})

const selectedCategory = computed(() =>
  categories.value.find((item) => item.code === form.category_code) ?? null,
)

const isCustomCategory = computed(() => !!selectedCategory.value && !selectedCategory.value.is_builtin)

const categoryDisplayName = computed(() => {
  if (categorySelectValue.value === CUSTOM_CATEGORY_VALUE) {
    return '+ 新建自定义分类'
  }
  return categories.value.find((item) => item.code === categorySelectValue.value)?.name || '请选择分类'
})

const availableContentTypes = computed(() => {
  if (isCustomCategory.value) {
    return ['url'] as Array<'url'>
  }
  const allowed = selectedCategory.value?.allowed_content_types
  if (!allowed?.length) {
    return ['url', 'text', 'qr_image'] as Array<'url' | 'text' | 'qr_image'>
  }
  return allowed
})

const parsedTags = computed(() =>
  form.tags_text
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean),
)

const canUseImageUpload = computed(() => form.content_type === 'qr_image')
const parsedSuccessItems = computed(() =>
  parsedImageResults.value.filter((item) => item.status === 'success' && item.decoded_url.trim()),
)

const imageSummary = computed(() => {
  if (!imageFiles.value.length) {
    return '未选择图片'
  }
  if (imageFiles.value.length === 1) {
    const first = imageFiles.value[0]
    return `已选择 1 张：${first ? first.name : ''}`
  }
  return `已选择 ${imageFiles.value.length} 张图片`
})

function nowLocalDateTimeValue(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

function plusHoursLocalDateTimeValue(hours: number): string {
  const time = new Date()
  time.setHours(time.getHours() + hours)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${time.getFullYear()}-${pad(time.getMonth() + 1)}-${pad(time.getDate())}T${pad(time.getHours())}:${pad(time.getMinutes())}`
}

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

async function loadCategories(): Promise<void> {
  try {
    categories.value = await listRedPacketCategories()
  } catch {
    categories.value = [
      {
        id: 0,
        name: '支付宝红包',
        code: 'alipay_red_packet',
        is_builtin: true,
        allowed_content_types: ['url', 'qr_image'],
      },
      {
        id: 0,
        name: '账号',
        code: 'account',
        is_builtin: true,
        allowed_content_types: ['text', 'url'],
      },
      {
        id: 0,
        name: '其他',
        code: 'misc',
        is_builtin: true,
        allowed_content_types: ['url', 'text', 'qr_image'],
      },
    ]
    message.value = '分类加载失败，已切换本地默认分类'
  }

  const preferred = categories.value.find((item) => item.code === form.category_code)
  const fallback = categories.value[0]
  form.category_code = preferred?.code || fallback?.code || ''
  categorySelectValue.value = form.category_code
}

function selectCategoryOption(value: string): void {
  categorySelectValue.value = value
  categoryMenuOpen.value = false
  if (value === CUSTOM_CATEGORY_VALUE) {
    showCustomCategoryInput.value = true
    form.content_type = 'url'
    return
  }
  showCustomCategoryInput.value = false
  form.category_code = value
}

function toggleCategoryMenu(): void {
  categoryMenuOpen.value = !categoryMenuOpen.value
}

function handleDocumentClick(event: MouseEvent): void {
  if (!categoryMenuRef.value) {
    return
  }
  const target = event.target as Node | null
  if (target && categoryMenuRef.value.contains(target)) {
    return
  }
  categoryMenuOpen.value = false
}

async function createCustomCategoryIfNeeded(): Promise<void> {
  if (!form.custom_category_name.trim()) {
    message.value = '请输入分类名称'
    return
  }

  loading.value = true
  message.value = ''
  try {
    const category = await createRedPacketCategory(form.custom_category_name.trim())
    await loadCategories()
    form.category_code = category.code
    categorySelectValue.value = category.code
    form.custom_category_name = ''
    showCustomCategoryInput.value = false
  } catch (error) {
    message.value = resolveErrorMessage(error, '创建自定义分类失败')
  } finally {
    loading.value = false
  }
}

function openImagePicker(): void {
  fileInputRef.value?.click()
}

function onImageFilesChange(event: Event): void {
  const target = event.target as HTMLInputElement
  imageFiles.value = Array.from(target.files || [])
  parseCurrentImages()
}

async function parseCurrentImages(): Promise<void> {
  parsedImageResults.value = []
  if (!imageFiles.value.length) {
    return
  }
  parsing.value = true
  message.value = ''
  try {
    const parsed = await parseImagesToUrls(imageFiles.value)
    parsedImageResults.value = parsed.results
    message.value = `解析完成：成功 ${parsed.success_count}，失败 ${parsed.failed_count}`
  } catch (error) {
    parsedImageResults.value = []
    message.value = resolveErrorMessage(error, '图片解析失败')
  } finally {
    parsing.value = false
  }
}

async function submit(): Promise<void> {
  if (!form.title.trim() && !canUseImageUpload.value) {
    message.value = '请填写红包名称'
    return
  }

  if (isCustomCategory.value) {
    form.content_type = 'url'
  }

  if (canUseImageUpload.value && !imageFiles.value.length) {
    message.value = '图片类型请至少上传一张图片'
    return
  }
  if (canUseImageUpload.value && !parsedSuccessItems.value.length) {
    message.value = '请先解析出至少一条可用链接再导入'
    return
  }

  const meta: Record<string, string> = {}
  if (form.red_packet_created_at) {
    meta.red_packet_created_at = form.red_packet_created_at
  }
  meta.red_packet_amount = String(form.amount || 0)
  if (form.category_code === 'account' && form.account_provider) {
    meta.account_provider = form.account_provider
  }

  loading.value = true
  message.value = ''
  try {
    if (canUseImageUpload.value) {
      await batchImportRedPacketUrls({
        titlePrefix: form.title.trim() || '支付宝红包',
        amount: Number(form.amount || 0),
        level: Number(form.level || 1),
        categoryCode: form.category_code,
        tags: parsedTags.value,
        availableFrom: form.available_from || null,
        availableTo: form.available_to || null,
        urls: parsedSuccessItems.value.map((item) => ({
          filename: item.filename,
          url: item.decoded_url,
        })),
      })
    } else {
      await createRedPacket({
        title: form.title,
        amount: Number(form.amount || 0),
        level: Number(form.level || 1),
        category_code: form.category_code,
        content_type: form.content_type,
        content_value: form.content_value,
        tags: parsedTags.value,
        meta,
        available_from: form.available_from || null,
        available_to: form.available_to || null,
      })
    }
    router.push('/red-packets?imported=1')
  } catch (error) {
    message.value = resolveErrorMessage(error, '导入失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [form.category_code, availableContentTypes.value.join(',')],
  () => {
    if (!availableContentTypes.value.includes(form.content_type)) {
      form.content_type = availableContentTypes.value[0] || 'url'
    }
    if (isCustomCategory.value) {
      form.content_type = 'url'
    }
  },
)

onMounted(() => {
  form.red_packet_created_at = nowLocalDateTimeValue()
  form.available_from = nowLocalDateTimeValue()
  form.available_to = plusHoursLocalDateTimeValue(24)
  loadCategories()
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<template>
  <section class="card-surface">
    <div class="head-row">
      <div>
        <h2 class="title">导入红包</h2>
        <p class="desc">单页完成单条与批量导入，支持链接、文本、图片内容。</p>
      </div>
      <button class="ghost-button" type="button" @click="router.push('/red-packets')">返回列表</button>
    </div>

    <div class="form-grid">
      <label class="field">
        <span>分类</span>
        <div ref="categoryMenuRef" class="dropdown">
          <button class="dropdown-trigger" type="button" @click="toggleCategoryMenu">
            <span>{{ categoryDisplayName }}</span>
            <span class="dropdown-arrow">▾</span>
          </button>
          <div v-if="categoryMenuOpen" class="dropdown-menu">
            <button
              v-for="item in categories"
              :key="item.code"
              class="dropdown-item"
              type="button"
              @click="selectCategoryOption(item.code)"
            >
              {{ item.name }}
            </button>
            <button class="dropdown-item" type="button" @click="selectCategoryOption(CUSTOM_CATEGORY_VALUE)">
              + 新建自定义分类
            </button>
          </div>
        </div>
      </label>

      <label class="field">
        <span>红包等级</span>
        <input v-model.number="form.level" class="input" min="1" max="10" type="number" />
      </label>

      <div v-if="showCustomCategoryInput" class="field full">
        <span>自定义分类名称（仅支持链接）</span>
        <div class="inline-row">
          <input v-model="form.custom_category_name" class="input" type="text" placeholder="例如：合作平台" />
          <button class="mini-button" type="button" :disabled="loading" @click="createCustomCategoryIfNeeded">创建并使用</button>
        </div>
      </div>

      <label class="field full">
        <span>红包名称（批量图片时作为标题前缀）</span>
        <input v-model="form.title" class="input" type="text" placeholder="支付宝红包 / 账号礼包" />
      </label>

      <label class="field">
        <span>内容类型</span>
        <div class="select-wrap">
          <select v-model="form.content_type" class="input select-input" :disabled="isCustomCategory">
            <option v-if="availableContentTypes.includes('url')" value="url">跳转链接</option>
            <option v-if="availableContentTypes.includes('text')" value="text">文本内容</option>
            <option v-if="availableContentTypes.includes('qr_image')" value="qr_image">二维码图片</option>
          </select>
        </div>
      </label>

      <label class="field">
        <span>金额（可为 0）</span>
        <input v-model.number="form.amount" class="input" min="0" step="0.01" type="number" />
      </label>

      <label class="field full">
        <span>标签（逗号分隔）</span>
        <input v-model="form.tags_text" class="input" type="text" placeholder="留空则不设置标签" />
      </label>

      <label v-if="!canUseImageUpload" class="field">
        <span>激活时间（可选）</span>
        <input v-model="form.available_from" class="input" type="datetime-local" />
      </label>

      <label v-if="!canUseImageUpload" class="field">
        <span>失效时间（可选）</span>
        <input v-model="form.available_to" class="input" type="datetime-local" />
      </label>

      <label v-if="!canUseImageUpload" class="field full">
        <span>内容</span>
        <textarea
          v-model="form.content_value"
          class="input textarea"
          :placeholder="form.content_type === 'url' ? 'https://example.com/redirect' : '请输入账号或文本内容'"
        ></textarea>
      </label>

      <div v-else class="field full">
        <span>图片文件（可多选）</span>
        <div class="upload-box" @click="openImagePicker">
          <p class="upload-title">点击选择二维码图片</p>
          <p class="upload-desc">支持多图导入，自动按名称前缀生成多条红包</p>
          <p class="upload-meta">{{ imageSummary }}</p>
        </div>
        <input ref="fileInputRef" class="file-hidden" multiple accept="image/*" type="file" @change="onImageFilesChange" />
      </div>

      <div v-if="canUseImageUpload" class="field full parse-result-field">
        <span>解析链接</span>
        <div class="parse-box">
          <p v-if="parsing" class="parse-tip">正在解析图片二维码...</p>
          <p v-else-if="!parsedImageResults.length" class="parse-tip">请选择图片后自动解析</p>
          <ul v-else class="parse-list">
            <li v-for="(item, idx) in parsedImageResults" :key="`${item.filename}-${item.decoded_url}-${idx}`" class="parse-item">
              <span class="parse-file">{{ item.filename }}</span>
              <span v-if="item.status === 'success'" class="parse-url">{{ item.decoded_url }}</span>
              <span v-else class="parse-failed">解析失败</span>
            </li>
          </ul>
        </div>
      </div>

      <label class="field">
        <span>红包创建时间</span>
        <input v-model="form.red_packet_created_at" class="input" type="datetime-local" />
      </label>

      <label v-if="form.category_code === 'account'" class="field">
        <span>账号平台</span>
        <input v-model="form.account_provider" class="input" type="text" placeholder="Google" />
      </label>
    </div>

    <button class="action-button" type="button" :disabled="loading" @click="submit">
      {{ loading ? '处理中...' : '保存并导入' }}
    </button>

    <p v-if="message" class="message">{{ message }}</p>
  </section>
</template>

<style scoped>
.head-row { align-items: center; display: flex; justify-content: space-between; gap: 10px; }
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.dropdown { position: relative; }
.dropdown-trigger {
  align-items: center;
  background: #fff;
  border: 1px solid #d8cdc3;
  border-radius: 10px;
  color: var(--color-text-main);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  min-height: 38px;
  padding: 8px 10px;
  width: 100%;
}
.dropdown-arrow { color: #85634f; }
.dropdown-menu {
  background: #fff;
  border: 1px solid #e2d5cb;
  border-radius: 10px;
  box-shadow: 0 8px 20px rgba(31, 18, 12, 0.08);
  display: grid;
  gap: 2px;
  left: 0;
  margin-top: 6px;
  padding: 6px;
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 12;
}
.dropdown-item {
  background: transparent;
  border: 0;
  border-radius: 8px;
  color: var(--color-text-main);
  cursor: pointer;
  padding: 8px 10px;
  text-align: left;
}
.dropdown-item:hover { background: #fff3e9; }
.input {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background: #fff;
  border: 1px solid #d8cdc3;
  border-radius: 10px;
  color: var(--color-text-main);
  font: inherit;
  padding: 8px 10px;
}
.select-wrap { position: relative; }
.select-wrap::after {
  content: '▾';
  pointer-events: none;
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #85634f;
}
.select-input { padding-right: 28px; }
.select-input::-ms-expand { display: none; }
.textarea { min-height: 96px; resize: vertical; }
.inline-row { display: grid; gap: 8px; grid-template-columns: 1fr auto; }
.upload-box {
  background: linear-gradient(135deg, #fff8f2, #ffeede);
  border: 1px dashed #d19a77;
  border-radius: 12px;
  cursor: pointer;
  padding: 14px;
}
.upload-title { font-weight: 600; margin: 0; }
.upload-desc { color: var(--color-text-secondary); margin: 6px 0 0; }
.upload-meta { color: #7d6b5e; font-size: 13px; margin: 8px 0 0; }
.file-hidden { display: none; }
.parse-result-field { margin-top: 2px; }
.parse-box { border: 1px solid #ead8cb; border-radius: 12px; background: #fff; padding: 10px; }
.parse-tip { margin: 0; color: var(--color-text-secondary); }
.parse-list { display: grid; gap: 6px; list-style: none; margin: 0; padding: 0; }
.parse-item { border: 1px solid #f0e4db; border-radius: 8px; display: grid; gap: 2px; padding: 8px; }
.parse-file { color: #6f5f52; font-size: 12px; }
.parse-url { color: var(--color-primary-deep); font-size: 13px; overflow-wrap: anywhere; }
.parse-failed { color: #b0452b; font-size: 13px; }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; margin-top: 12px; padding: 8px 12px; cursor: pointer; }
.ghost-button { border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); border-radius: 10px; background: transparent; color: var(--color-text-main); cursor: pointer; padding: 8px 12px; }
.mini-button { border: 0; border-radius: 10px; background: var(--color-primary-soft); color: var(--color-primary-deep); cursor: pointer; padding: 8px 10px; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
@media (max-width: 900px) {
  .head-row { align-items: flex-start; flex-direction: column; }
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
}
</style>
