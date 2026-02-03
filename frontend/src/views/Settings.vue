<template>
  <div class="settings-container">
    <el-card>
      <template #header>
        <h2>配置管理</h2>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 模型配置 -->
        <el-tab-pane label="模型配置" name="model">
          <el-form :model="modelConfig" :rules="modelRules" ref="modelFormRef" label-width="120px">
            <el-form-item label="API密钥" prop="api_key">
              <el-input v-model="modelConfig.api_key" type="password" show-password placeholder="请输入API密钥" />
            </el-form-item>
            <el-form-item label="API地址" prop="base_url">
              <el-input v-model="modelConfig.base_url" placeholder="https://api.openai.com/v1" />
            </el-form-item>
            <el-form-item label="模型名称" prop="model">
              <el-input v-model="modelConfig.model" placeholder="gpt-3.5-turbo" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleTestModelConfig" :loading="testing">测试连接</el-button>
              <el-button type="success" @click="saveModelConfig" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- GitLab配置 -->
        <el-tab-pane label="GitLab配置" name="gitlab">
          <el-form :model="gitlabConfig" :rules="gitlabRules" ref="gitlabFormRef" label-width="120px">
            <el-form-item label="GitLab地址" prop="url">
              <el-input v-model="gitlabConfig.url" placeholder="https://gitlab.example.com" />
            </el-form-item>
            <el-form-item label="访问令牌" prop="token">
              <el-input v-model="gitlabConfig.token" type="password" show-password placeholder="请输入GitLab Access Token" />
            </el-form-item>
            <el-form-item>
              <el-button type="success" @click="saveGitlabConfig" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- MySQL配置 -->
        <el-tab-pane label="MySQL配置" name="mysql">
          <el-form :model="mysqlConfig" :rules="mysqlRules" ref="mysqlFormRef" label-width="120px">
            <el-form-item label="数据库主机" prop="host">
              <el-input v-model="mysqlConfig.host" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="mysqlConfig.port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名" prop="user">
              <el-input v-model="mysqlConfig.user" placeholder="root" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="mysqlConfig.password" type="password" show-password placeholder="请输入密码" />
            </el-form-item>
            <el-form-item label="数据库名" prop="database">
              <el-input v-model="mysqlConfig.database" placeholder="database_name" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleTestMysqlConfig" :loading="testingMysql">测试连接</el-button>
              <el-button type="success" @click="saveMysqlConfig" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { 
  getConfig, 
  updateModelConfig, 
  updateMySQLConfigWithSync, 
  testModelConfig as apiTestModelConfig,
  testMySQLConfig,
  type ModelConfig, 
  type MySQLConfig,
  type SyncResult
} from '@/api/config'

const activeTab = ref('model')
const saving = ref(false)
const testing = ref(false)
const testingMysql = ref(false)

const modelFormRef = ref<FormInstance>()
const gitlabFormRef = ref<FormInstance>()
const mysqlFormRef = ref<FormInstance>()

const modelConfig = reactive<ModelConfig>({
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model: 'gpt-3.5-turbo'
})

const gitlabConfig = reactive({
  url: '',
  token: ''
})

const mysqlConfig = reactive<MySQLConfig>({
  host: '',
  port: 3306,
  user: '',
  password: '',
  database: ''
})

const modelRules: FormRules = {
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }],
  base_url: [
    { required: true, message: '请输入API地址', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' }
  ],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

const gitlabRules: FormRules = {
  url: [{ required: true, message: '请输入GitLab地址', trigger: 'blur' }],
  token: [{ required: true, message: '请输入访问令牌', trigger: 'blur' }]
}

const mysqlRules: FormRules = {
  host: [{ required: true, message: '请输入数据库主机', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  user: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  database: [{ required: true, message: '请输入数据库名', trigger: 'blur' }]
}

onMounted(async () => {
  await loadConfig()
})

const loadConfig = async () => {
  try {
    const config = await getConfig()
    if (config.model_config) {
      Object.assign(modelConfig, config.model_config)
    }
    if (config.gitlab_config) {
      Object.assign(gitlabConfig, config.gitlab_config)
    }
    if (config.mcp_config && config.mcp_config.mysql) {
      Object.assign(mysqlConfig, config.mcp_config.mysql)
    }
  } catch (error) {
    ElMessage.error('加载配置失败')
  }
}

const handleTestModelConfig = async () => {
  testing.value = true
  try {
    const result = await apiTestModelConfig(modelConfig)
    if (result.code === 0) {
      ElMessage.success('模型配置测试成功')
    } else {
      ElMessage.error(result.message || '测试失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '测试失败')
  } finally {
    testing.value = false
  }
}

const saveModelConfig = async () => {
  saving.value = true
  try {
    await updateModelConfig(modelConfig)
    ElMessage.success('模型配置保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const saveGitlabConfig = async () => {
  saving.value = true
  try {
    await fetch('/api/v1/config/gitlab', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(gitlabConfig)
    })
    ElMessage.success('GitLab配置保存成功')
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleTestMysqlConfig = async () => {
  testingMysql.value = true
  try {
    const result = await testMySQLConfig(mysqlConfig)
    if (result.code === 0) {
      ElMessage.success('MySQL连接测试成功')
    } else {
      ElMessage.error(result.message || '测试失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '测试失败')
  } finally {
    testingMysql.value = false
  }
}

const saveMysqlConfig = async () => {
  saving.value = true
  try {
    const result = await updateMySQLConfigWithSync(mysqlConfig)
    
    if (result.code === 0 && result.sync?.success) {
      // 保存成功且同步成功
      ElMessage.success('MySQL配置保存成功，' + result.sync.message)
    } else if (result.code === 1 && result.sync && !result.sync.success) {
      // 保存成功但同步失败
      ElMessage.warning('MySQL配置保存成功，但' + result.sync.message)
    } else {
      ElMessage.success('MySQL配置保存成功')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-container {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.settings-container h2 {
  margin: 0;
  color: #303133;
}
</style>
