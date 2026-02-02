<template>
  <div class="users-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>用户管理</h2>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            添加用户
          </el-button>
        </div>
      </template>

      <el-table :data="users" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'success'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button
              v-if="row.username !== 'admin'"
              type="warning"
              size="small"
              @click="handleResetPassword(row.id)"
            >
              重置密码
            </el-button>
            <el-button
              v-if="row.username !== 'admin'"
              type="danger"
              size="small"
              @click="handleDelete(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加用户对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="添加用户"
      width="500px"
    >
      <el-form :model="createForm" :rules="rules" ref="createFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="loading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog
      v-model="showResetDialog"
      title="重置密码"
      width="400px"
    >
      <el-form :model="resetForm" :rules="resetRules" ref="resetFormRef" label-width="80px">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="resetForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetDialog = false">取消</el-button>
        <el-button type="primary" @click="handleReset" :loading="loading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, deleteUser, resetUserPassword } from '@/api/auth'
import type { User } from '@/types'

const users = ref<User[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showResetDialog = ref(false)

const createFormRef = ref<FormInstance>()
const resetFormRef = ref<FormInstance>()

const createForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const resetForm = reactive({
  new_password: ''
})

const selectedUserId = ref<number | null>(null)

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3到20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

const resetRules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ]
}

onMounted(() => {
  loadUsers()
})

const loadUsers = async () => {
  try {
    const data = await getUsers()
    users.value = data
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  }
}

const handleCreate = async () => {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await createUser(createForm)
      ElMessage.success('创建用户成功')
      showCreateDialog.value = false
      createForm.username = ''
      createForm.password = ''
      createForm.role = 'user'
      await loadUsers()
    } catch (error: any) {
      ElMessage.error(error.message || '创建用户失败')
    } finally {
      loading.value = false
    }
  })
}

const handleDelete = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除此用户吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteUser(id)
    ElMessage.success('删除成功')
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleResetPassword = (id: number) => {
  selectedUserId.value = id
  resetForm.new_password = ''
  showResetDialog.value = true
}

const handleReset = async () => {
  if (!resetFormRef.value || selectedUserId.value === null) return

  await resetFormRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await resetUserPassword(selectedUserId.value, resetForm)
      ElMessage.success('重置密码成功')
      showResetDialog.value = false
      resetForm.new_password = ''
    } catch (error: any) {
      ElMessage.error(error.message || '重置密码失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.users-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}
</style>
