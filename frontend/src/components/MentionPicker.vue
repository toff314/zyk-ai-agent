<template>
  <div
    v-if="visible"
    class="mention-picker"
    :style="{ top: `${position.y}px`, left: `${position.x}px` }"
  >
    <div class="mention-header">
      <span>{{ title }}</span>
    </div>
    <div class="mention-search" v-if="showSearch">
      <el-input
        v-model="searchQuery"
        placeholder="搜索..."
        size="small"
        clearable
      />
    </div>
    <div class="mention-list">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="mention-item"
        :class="{ active: selectedIndex === index }"
        @click="selectItem(item)"
      >
        <div class="mention-avatar" v-if="item.avatar_url">
          <img :src="item.avatar_url" :alt="item.name" />
        </div>
        <div class="mention-info">
          <div class="mention-name">{{ item.name }}</div>
          <div class="mention-desc" v-if="item.description">
            {{ item.description }}
          </div>
        </div>
      </div>
      <div v-if="filteredItems.length === 0" class="mention-empty">
        无匹配项
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import type { MentionItem } from '@/types'

interface Props {
  visible: boolean
  items: MentionItem[]
  position: { x: number; y: number }
  type: 'user' | 'database' | 'table'
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  items: () => [],
  type: 'user'
})

const emit = defineEmits<{
  (e: 'select', item: MentionItem): void
  (e: 'close'): void
}>()

const searchQuery = ref('')
const selectedIndex = ref(0)

const title = computed(() => {
  const titles = {
    user: '选择研发人员',
    database: '选择数据库',
    table: '选择表'
  }
  return titles[props.type]
})

const showSearch = computed(() => {
  return props.items.length > 5
})

const filteredItems = computed(() => {
  if (!searchQuery.value) {
    return props.items
  }
  const query = searchQuery.value.toLowerCase()
  return props.items.filter(item =>
    item.name.toLowerCase().includes(query) ||
    (item.description && item.description.toLowerCase().includes(query))
  )
})

const selectItem = (item: MentionItem) => {
  emit('select', item)
  emit('close')
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (!props.visible) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, filteredItems.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (filteredItems.value[selectedIndex.value]) {
      selectItem(filteredItems.value[selectedIndex.value])
    }
  } else if (e.key === 'Escape') {
    emit('close')
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    selectedIndex.value = 0
    searchQuery.value = ''
    document.addEventListener('keydown', handleKeyDown)
  } else {
    document.removeEventListener('keydown', handleKeyDown)
  }
})

onMounted(() => {
  document.addEventListener('click', (e) => {
    const picker = document.querySelector('.mention-picker')
    if (picker && !picker.contains(e.target as Node)) {
      emit('close')
    }
  })
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.mention-picker {
  position: fixed;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  z-index: 9999;
  min-width: 250px;
  max-width: 400px;
  max-height: 300px;
  overflow: hidden;
}

.mention-header {
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  font-weight: 500;
  font-size: 13px;
  color: #606266;
}

.mention-search {
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
}

.mention-list {
  overflow-y: auto;
  max-height: 200px;
}

.mention-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.mention-item:hover,
.mention-item.active {
  background: #f5f7fa;
}

.mention-avatar {
  width: 32px;
  height: 32px;
  margin-right: 10px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.mention-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mention-info {
  flex: 1;
  min-width: 0;
}

.mention-name {
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mention-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mention-empty {
  padding: 20px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style>
