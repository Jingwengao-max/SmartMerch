<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import LayerEditor from '@/components/studio/LayerEditor.vue'
import {
  fetchPosterTemplate,
  generateFromPosterTemplate,
  listPosterTemplates,
  type PosterDocument,
  type PosterTemplate,
  type PosterTemplateSummary,
} from '@/services/posterApi'

const route = useRoute()
const templates = ref<PosterTemplateSummary[]>([])
const selectedId = ref('')
const template = ref<PosterTemplate | null>(null)
const productFile = ref<File | null>(null)
const productPreview = ref('')
const content = reactive<Record<string, string | string[]>>({})
const generating = ref(false)
const error = ref('')
const result = ref<{ jobId: string; document: PosterDocument; previewUrl: string } | null>(null)

const editableFields = computed(() => (template.value?.fields || []).filter(
  (field) => field.type !== 'image',
))
const canGenerate = computed(() => !!template.value && !!productFile.value && !generating.value)
async function loadTemplate(templateId: string) {
  if (!templateId) return
  selectedId.value = templateId
  result.value = null
  error.value = ''
  try {
    template.value = await fetchPosterTemplate(templateId)
    Object.keys(content).forEach((key) => delete content[key])
    for (const field of template.value.fields) {
      if (field.type === 'image') continue
      const key = String(field.key)
      const layers = template.value.layers.filter(
        (layer) => String(layer.bindTo || '') === key,
      )
      const defaults = layers.map((layer) => String(layer.defaultText || '')).filter(Boolean)
      content[key] = defaults.join('\n')
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '模板加载失败'
  }
}

function chooseProduct(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  productFile.value = file
  if (productPreview.value.startsWith('blob:')) URL.revokeObjectURL(productPreview.value)
  productPreview.value = URL.createObjectURL(file)
  result.value = null
}

async function generate() {
  if (!template.value || !productFile.value || generating.value) return
  generating.value = true
  error.value = ''
  try {
    result.value = await generateFromPosterTemplate({
      templateId: template.value.templateId,
      image: productFile.value,
      content: { ...content },
    })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '模板生成失败'
  } finally {
    generating.value = false
  }
}

function updateDocument(document: PosterDocument) {
  if (result.value) result.value.document = document
}

onMounted(async () => {
  try {
    templates.value = await listPosterTemplates()
    const requested = String(route.query.template || '')
    await loadTemplate(requested || templates.value[0]?.templateId || '')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '模板列表加载失败'
  }
})

onBeforeUnmount(() => {
  if (productPreview.value.startsWith('blob:')) URL.revokeObjectURL(productPreview.value)
})
</script>

<template>
  <div class="min-h-screen bg-paper text-ink">
    <header class="flex h-16 items-center justify-between border-b border-warm-300 px-5 md:px-8">
      <RouterLink to="/template-import" class="btn-link text-sm">← 返回模板解析</RouterLink>
      <div class="text-center">
        <p class="font-display text-xl">使用模板生成海报</p>
        <p class="font-mono text-[10px] tracking-[0.18em] text-ink-faint">TEMPLATE → PRODUCT POSTER</p>
      </div>
      <span class="font-mono text-[10px] text-ink-faint">P0 WORKFLOW</span>
    </header>

    <main class="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[320px_minmax(0,1fr)] md:px-8">
      <aside class="space-y-4">
        <section class="border border-warm-300 bg-paper p-4">
          <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">TEMPLATE</p>
          <select
            class="field-input mt-2"
            :value="selectedId"
            @change="loadTemplate(($event.target as HTMLSelectElement).value)"
          >
            <option value="" disabled>选择模板</option>
            <option v-for="item in templates" :key="item.templateId" :value="item.templateId">
              {{ item.name }}
            </option>
          </select>
          <p v-if="template" class="mt-3 text-xs text-ink-faint">
            {{ template.layers.length }} 图层 · {{ template.fields.length }} 字段
          </p>
        </section>

        <section class="border border-warm-300 bg-paper p-4">
          <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">NEW PRODUCT</p>
          <h1 class="mt-1 font-display text-2xl">上传新商品</h1>
          <label class="mt-3 block">
            <span class="btn-rect w-full justify-center text-xs">选择商品照片</span>
            <input class="hidden" type="file" accept="image/png,image/jpeg,image/webp" @change="chooseProduct" />
          </label>
          <img v-if="productPreview" :src="productPreview" alt="商品" class="mt-3 max-h-52 w-full object-contain" />
        </section>

        <section v-if="template" class="border border-warm-300 bg-paper p-4">
          <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">CONTENT</p>
          <h2 class="mt-1 font-display text-2xl">填写模板内容</h2>
          <div class="mt-3 space-y-3">
            <label v-for="field in editableFields" :key="String(field.key)" class="block text-xs text-ink-soft">
              {{ field.label || field.key }}
              <input
                v-model="content[String(field.key)]"
                class="field-input mt-1"
                :maxlength="Number(field.maxChars || 60)"
                :placeholder="String(field.label || field.key)"
              />
            </label>
          </div>
          <button class="btn-cta mt-4 w-full" :disabled="!canGenerate" @click="generate">
            {{ generating ? '生成中…' : '生成可编辑海报' }}
          </button>
          <p v-if="error" class="mt-2 text-xs text-red-700">{{ error }}</p>
        </section>
      </aside>

      <section class="min-w-0">
        <template v-if="result">
          <div class="mb-4 flex items-end justify-between">
            <div>
              <p class="font-mono text-[10px] tracking-[0.16em] text-sage">GENERATED</p>
              <h2 class="mt-1 font-display text-3xl">可编辑海报已生成</h2>
            </div>
            <span class="font-mono text-xs text-ink-faint">Job {{ result.jobId }}</span>
          </div>
          <LayerEditor :document="result.document" @update:document="updateDocument" />
        </template>
        <div v-else class="flex min-h-[600px] items-center justify-center border border-dashed border-warm-300 text-sm text-ink-faint">
          选择模板并上传商品后生成海报
        </div>
      </section>
    </main>
  </div>
</template>
