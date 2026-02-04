<template>
  <div class="chat-container">
    <!-- 侧边栏：对话历史 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>对话历史</h3>
        <el-button type="primary" size="small" @click="createNewChat">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>
      <div class="sidebar-content">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conversation-item"
          :class="{ active: currentConversationId === conv.id }"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">
            <el-tag size="small" :type="getModeType(conv.mode)">
              {{ getModeName(conv.mode) }}
            </el-tag>
            <el-button
              type="danger"
              size="small"
              text
              @click.stop="deleteConversation(conv.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主聊天区域 -->
    <div class="chat-main">
      <!-- 顶部：模式切换 -->
      <div class="chat-header">
        <div class="mode-switch">
          <el-radio-group v-model="currentMode" :disabled="!!currentConversationId">
            <el-radio-button label="normal">普通对话</el-radio-button>
            <el-radio-button label="data_analysis" :disabled="!isLoggedIn">数据分析</el-radio-button>
            <el-radio-button label="code_review" :disabled="!isLoggedIn">研发质量</el-radio-button>
          </el-radio-group>
        </div>
        <div class="chat-hint">选择模式后开始对话</div>
      </div>

      <!-- 消息显示区域 -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="empty-state">
          <el-empty description="开始一个新对话吧" />
        </div>
        <div v-else class="messages-list">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message"
            :class="msg.role"
          >
            <div class="message-avatar">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
              <el-icon v-else><ChatDotSquare /></el-icon>
            </div>
            <div class="message-content">
              <div class="message-role">{{ msg.role === 'user' ? '你' : 'AI助手' }}</div>
              <MarkdownRenderer :content="msg.content" />
            </div>
          </div>
        </div>
        
        <!-- 加载中提示 -->
        <div v-if="loading" class="message assistant loading">
          <div class="message-avatar">
            <el-icon><ChatDotSquare /></el-icon>
          </div>
          <div class="message-content">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>思考中...</span>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="输入消息... (@选择对象，#快捷模板)"
            @input="handleInput"
            @keydown="handleKeyDown"
            :disabled="loading"
          />
          <div class="input-actions">
            <el-button
              type="primary"
              @click="sendMessage"
              :loading="loading"
              :disabled="!inputMessage.trim()"
            >
              发送
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- @选择弹框 -->
    <MentionPicker
      v-if="mentionVisible"
      :visible="mentionVisible"
      :items="mentionItems"
      :position="mentionPosition"
      :type="mentionType"
      @select="handleMentionSelect"
      @close="mentionVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Delete,
  User,
  ChatDotSquare,
  Loading
} from '@element-plus/icons-vue'
import {
  chatStream,
  getConversations,
  getMessages,
  deleteConversation as deleteConv,
  getGitLabUsers,
  getMysqlDatabases,
  getMysqlTables,
  getChatTemplates,
  type ChatRequest
} from '@/api/chat'
import { useUserStore } from '@/store/user'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import MentionPicker from '@/components/MentionPicker.vue'
import type { Conversation, Message, StreamResponse, GitLabUser, MysqlDatabase, MysqlTable, MentionItem, ChatTemplate } from '@/types'
import { replaceTriggerText } from '@/utils/triggerInsert'

const userStore = useUserStore()

const conversations = ref<Conversation[]>([])
const messages = ref<Message[]>([])
const currentConversationId = ref<number | null>(null)
const currentMode = ref<'normal' | 'data_analysis' | 'code_review'>('normal')
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref<HTMLElement>()

// @选择相关
const mentionVisible = ref(false)
const mentionPosition = ref({ x: 0, y: 0 })
const mentionType = ref<'user' | 'database' | 'table' | 'template'>('user')
const mentionItems = ref<MentionItem[]>([])
const mentionTriggerIndex = ref<number | null>(null)
const mentionTriggerChar = ref<'@' | '#' | null>(null)
const templateCache = ref<Record<string, MentionItem[]>>({})
const cursorPosition = ref(0)
const inputEl = ref<HTMLInputElement>()
const mysqlDatabases = ref<MysqlDatabase[]>([])
const mysqlTables = ref<Record<string, MysqlTable[]>>({})
const selectedDatabase = ref<string | null>(null)

const isLoggedIn = computed(() => !!userStore.user)

onMounted(async () => {
  await loadConversations()
  await consumePendingChatRequest()
})

const loadConversations = async () => {
  try {
    const data = await getConversations()
    conversations.value = data
  } catch (error) {
    ElMessage.error('加载对话列表失败')
  }
}

const loadMessages = async (conversationId: number) => {
  try {
    const data = await getMessages(conversationId)
    messages.value = data
    scrollToBottom()
  } catch (error) {
    ElMessage.error('加载消息失败')
  }
}

const createNewChat = () => {
  currentConversationId.value = null
  messages.value = []
  inputMessage.value = ''
}

const selectConversation = async (id: number) => {
  currentConversationId.value = id
  await loadMessages(id)
  const conv = conversations.value.find(c => c.id === id)
  if (conv) {
    currentMode.value = conv.mode
  }
}

const deleteConversation = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteConv(id)
    if (currentConversationId.value === id) {
      createNewChat()
    }
    await loadConversations()
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const sendMessageWithPayload = async (payload: { message: string; review_diff?: string; review_notice?: string }) => {
  const message = payload.message.trim()
  if (!message) return

  inputMessage.value = ''
  loading.value = true

  try {
    // 生成消息ID
    const userMessageId = Date.now()
    const aiMessageId = Date.now() + 1
    
    // 先添加用户消息到界面
    messages.value.push({
      id: userMessageId,
      conversation_id: currentConversationId.value || -1,
      role: 'user',
      content: message,
      created_at: new Date().toISOString()
    })

    // 添加空的AI消息占位
    messages.value.push({
      id: aiMessageId,
      conversation_id: currentConversationId.value || -1,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    })

    scrollToBottom()

    // 准备请求
    const chatData: ChatRequest = {
      message,
      mode: currentMode.value,
      conversation_id: currentConversationId.value,
      review_diff: payload.review_diff,
      review_notice: payload.review_notice
    }

    let fullResponse = ''
    let newConversationId: number | null = null

    await chatStream(
      chatData,
      (response: StreamResponse) => {
        if (response.type === 'conversation_id') {
          newConversationId = response.id
          currentConversationId.value = response.id
        } else if (response.type === 'chunk') {
          fullResponse += response.content
          // 更新AI消息内容
          const aiMsg = messages.value.find(m => m.id === aiMessageId)
          if (aiMsg) {
            aiMsg.content = fullResponse
            scrollToBottom()
          }
        } else if (response.type === 'done') {
          loading.value = false
          if (newConversationId) {
            // 更新新消息的conversation_id
            const userMsg = messages.value.find(m => m.id === userMessageId)
            const aiMsg = messages.value.find(m => m.id === aiMessageId)
            if (userMsg) userMsg.conversation_id = newConversationId
            if (aiMsg) aiMsg.conversation_id = newConversationId
            loadConversations()
          }
        }
      },
      (error) => {
        console.error('流式对话出错:', error)
        ElMessage.error(error.message || '发送失败')
        loading.value = false
        // 移除未完成的AI消息
        const aiMsgIndex = messages.value.findIndex(m => m.id === aiMessageId)
        if (aiMsgIndex !== -1) {
          messages.value.splice(aiMsgIndex, 1)
        }
      }
    )

  } catch (error: any) {
    console.error('发送消息失败:', error)
    ElMessage.error(error.message || '发送失败')
    loading.value = false
  }
}

const sendMessage = async () => {
  if (loading.value) return
  await sendMessageWithPayload({ message: inputMessage.value })
}

const findTriggerIndex = (value: string, cursor: number, trigger: '@' | '#') => {
  const index = value.lastIndexOf(trigger, cursor - 1)
  if (index === -1) return null
  if (index > 0) {
    const prev = value[index - 1]
    if (prev !== ' ' && prev !== '\n') return null
  }
  const textAfter = value.slice(index + 1, cursor)
  if (textAfter.includes(' ') || textAfter.includes('\n')) return null
  return index
}

const handleInput = async (value: string) => {
  const textarea = document.querySelector('.el-textarea__inner') as HTMLTextAreaElement
  if (textarea) {
    cursorPosition.value = textarea.selectionStart
  }

  const atIndex = findTriggerIndex(value, cursorPosition.value, '@')
  const hashIndex = findTriggerIndex(value, cursorPosition.value, '#')

  let triggerChar: '@' | '#' | null = null
  let triggerIndex: number | null = null

  if (atIndex !== null && (hashIndex === null || atIndex > hashIndex)) {
    triggerChar = '@'
    triggerIndex = atIndex
  } else if (hashIndex !== null) {
    triggerChar = '#'
    triggerIndex = hashIndex
  }

  if (!triggerChar || triggerIndex === null) {
    mentionVisible.value = false
    mentionTriggerIndex.value = null
    mentionTriggerChar.value = null
    return
  }

  mentionTriggerIndex.value = triggerIndex
  mentionTriggerChar.value = triggerChar

  if (textarea) {
    const rect = textarea.getBoundingClientRect()
    const text = textarea.value.substring(0, cursorPosition.value)
    const lines = text.split('\n')
    const line = lines.length
    const char = lines[lines.length - 1].length

    mentionPosition.value = {
      x: rect.left + char * 8 + 20,
      y: rect.top + line * 24 + 60
    }
  }

  if (triggerChar === '@') {
    // 根据模式@选择不同的内容
    if (currentMode.value === 'data_analysis') {
      if (selectedDatabase.value) {
        const databaseName = selectedDatabase.value
        mentionType.value = 'table'
        if (!mysqlTables.value[databaseName]) {
          try {
            const tables = await getMysqlTables(databaseName)
            mysqlTables.value = { ...mysqlTables.value, [databaseName]: tables }
          } catch (error) {
            mysqlTables.value = { ...mysqlTables.value, [databaseName]: [] }
          }
        }
        const tables = mysqlTables.value[databaseName] || []
        const tableItems = tables.map((table: MysqlTable) => ({
          id: `${databaseName}.${table.name}`,
          name: table.remark || table.name,
          raw_name: table.name,
          type: 'table',
          description: table.comment || table.type || databaseName
        }))
        mentionItems.value = [
          {
            id: '__reset_db__',
            name: '切换数据库',
            type: 'database',
            description: `当前: ${databaseName}`
          },
          ...tableItems
        ]
      } else {
        mentionType.value = 'database'
        if (mysqlDatabases.value.length === 0) {
          try {
            mysqlDatabases.value = await getMysqlDatabases()
          } catch (error) {
            mysqlDatabases.value = []
          }
        }
        mentionItems.value = mysqlDatabases.value.map((db: MysqlDatabase) => ({
          id: db.name,
          name: db.remark || db.name,
          raw_name: db.name,
          type: 'database'
        }))
      }
    } else if (currentMode.value === 'code_review' && isLoggedIn.value) {
      mentionType.value = 'user'
      try {
        const users = await getGitLabUsers()
        mentionItems.value = users.map((u: GitLabUser) => ({
          id: u.id,
          name: u.remark || u.name || u.username,
          type: 'user',
          avatar_url: u.avatar_url,
          description: `本周提交: ${u.commits_week} 次`
        }))
      } catch (error) {
        mentionItems.value = []
      }
    } else {
      mentionItems.value = []
    }
  } else {
    mentionType.value = 'template'
    const modeKey = currentMode.value
    if (!templateCache.value[modeKey]) {
      try {
        const templates = await getChatTemplates(modeKey)
        templateCache.value[modeKey] = templates.map((t: ChatTemplate) => ({
          id: t.id,
          name: t.name,
          type: 'template',
          description: t.description,
          content: t.content
        }))
      } catch (error) {
        templateCache.value[modeKey] = []
      }
    }
    mentionItems.value = templateCache.value[modeKey]
  }

  mentionVisible.value = true
}

const handleMentionSelect = (item: MentionItem) => {
  const fallbackIndex = mentionTriggerChar.value === '#'
    ? inputMessage.value.lastIndexOf('#')
    : inputMessage.value.lastIndexOf('@')
  const triggerIndex = mentionTriggerIndex.value ?? fallbackIndex
  const afterMention = inputMessage.value.slice(cursorPosition.value)

  if (item.type === 'template') {
    const replacement = item.content || item.name
    if (triggerIndex !== -1) {
      inputMessage.value = replaceTriggerText(
        inputMessage.value,
        triggerIndex,
        cursorPosition.value,
        replacement
      )
    }
    mentionVisible.value = false
    mentionTriggerIndex.value = null
    mentionTriggerChar.value = null

    nextTick(() => {
      const textarea = document.querySelector('.el-textarea__inner') as HTMLTextAreaElement
      if (textarea) {
        textarea.focus()
      }
    })
    return
  }

  const beforeMention = triggerIndex === -1
    ? inputMessage.value
    : inputMessage.value.slice(0, triggerIndex)

  if (item.type === 'database') {
    if (item.id === '__reset_db__') {
      selectedDatabase.value = null
      mentionVisible.value = false
      mentionTriggerIndex.value = null
      mentionTriggerChar.value = null
      return
    }
    selectedDatabase.value = item.raw_name || item.name
  }

  const mentionText = `@${item.name} `
  inputMessage.value = beforeMention + mentionText + afterMention
  mentionVisible.value = false
  mentionTriggerIndex.value = null
  mentionTriggerChar.value = null
  
  // 聚焦输入框
  nextTick(() => {
    const textarea = document.querySelector('.el-textarea__inner') as HTMLTextAreaElement
    if (textarea) {
      textarea.focus()
    }
  })
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
  cursorPosition.value = (e.target as HTMLTextAreaElement).selectionStart
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const consumePendingChatRequest = async () => {
  const raw = sessionStorage.getItem('pending_chat_request')
  if (!raw) return

  sessionStorage.removeItem('pending_chat_request')
  try {
    const payload = JSON.parse(raw)
    if (!payload?.message) return
    createNewChat()
    currentMode.value = payload.mode || 'code_review'
    await sendMessageWithPayload({
      message: payload.message,
      review_diff: payload.review_diff,
      review_notice: payload.review_notice
    })
  } catch (error) {
    console.error('解析待发送请求失败:', error)
  }
}

const getModeName = (mode: string) => {
  const names = {
    normal: '普通',
    data_analysis: '数据分析',
    code_review: '代码审查'
  }
  return names[mode] || mode
}

const getModeType = (mode: string) => {
  const types = {
    normal: '',
    data_analysis: 'success',
    code_review: 'warning'
  }
  return types[mode] || ''
}

</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100%;
  min-height: 0;
  background: #f5f7fa;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-item {
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 8px;
  transition: all 0.2s;
}

.conversation-item:hover {
  background: #f5f7fa;
}

.conversation-item.active {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
}

.conv-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-header {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-hint {
  font-size: 13px;
  color: #909399;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  min-height: 0;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.message.user .message-avatar {
  background: #409eff;
  color: white;
}

.message.assistant .message-avatar {
  background: #67c23a;
  color: white;
}

.message.loading .message-avatar {
  background: #909399;
  color: white;
}

.message-content {
  max-width: 70%;
  background: white;
  padding: 12px 16px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.message.assistant .message-content {
  max-width: 840px;
}

.message.user .message-content {
  max-width: 360px;
}

.message.user .message-content {
  background: #409eff;
  color: white;
}

.message.loading .message-content {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.message-role {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.message.user .message-role {
  text-align: right;
  color: rgba(255, 255, 255, 0.8);
}

.input-area {
  background: white;
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
}

.input-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
