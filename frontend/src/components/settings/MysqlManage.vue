<template>
  <div class="manage-section">
    <div class="toolbar">
      <el-button type="primary" @click="loadDatabases(true)">刷新</el-button>
    </div>
    <el-table :data="databases" v-loading="loading" row-key="id">
      <el-table-column label="数据库" min-width="200">
        <template #default="scope">
          <div class="name-cell">
            <div class="primary">{{ displayName(scope.row.name, scope.row.remark) }}</div>
            <div class="secondary">{{ scope.row.name }}</div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="table_count" label="表数量" width="100" />
      <el-table-column label="启用" width="100">
        <template #default="scope">
          <el-switch v-model="scope.row.enabled" @change="toggleDatabase(scope.row)" />
        </template>
      </el-table-column>
      <el-table-column label="备注" min-width="180">
        <template #default="scope">
          <el-input
            v-model="scope.row.remark"
            placeholder="备注"
            @blur="updateDatabaseRemark(scope.row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="scope">
          <el-button size="small" @click="openTables(scope.row)">查看表</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pagination">
      <el-pagination
        v-model:current-page="databasePager.page"
        v-model:page-size="databasePager.pageSize"
        :page-sizes="PAGE_SIZE_OPTIONS"
        :total="databasePager.total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleDatabasePageChange"
        @current-change="handleDatabasePageChange"
      />
    </div>

    <el-drawer v-model="tablesVisible" :title="tablesTitle" size="60%">
      <div class="drawer-toolbar">
        <el-button type="primary" @click="loadTables(true)">刷新</el-button>
      </div>
      <el-table :data="tables" v-loading="tablesLoading" row-key="id">
        <el-table-column label="表名" min-width="200">
          <template #default="scope">
            <div class="name-cell">
              <div class="primary">{{ displayName(scope.row.name, scope.row.remark) }}</div>
              <div class="secondary">{{ scope.row.name }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="comment" label="注释" min-width="200" />
        <el-table-column label="启用" width="100">
          <template #default="scope">
            <el-switch v-model="scope.row.enabled" @change="toggleTable(scope.row)" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="180">
          <template #default="scope">
            <el-input
              v-model="scope.row.remark"
              placeholder="备注"
              @blur="updateTableRemark(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
        <template #default="scope">
          <el-button size="small" @click="openTableDetail(scope.row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
      <div class="pagination">
        <el-pagination
          v-model:current-page="tablePager.page"
          v-model:page-size="tablePager.pageSize"
          :page-sizes="PAGE_SIZE_OPTIONS"
          :total="tablePager.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleTablePageChange"
          @current-change="handleTablePageChange"
        />
      </div>
    </el-drawer>

    <el-drawer v-model="detailVisible" title="表结构" size="50%">
      <el-table :data="tableDetail" v-loading="detailLoading" row-key="Field">
        <el-table-column prop="Field" label="字段" width="160" />
        <el-table-column prop="Type" label="类型" width="180" />
        <el-table-column prop="Null" label="可空" width="80" />
        <el-table-column prop="Key" label="键" width="80" />
        <el-table-column prop="Default" label="默认值" width="120" />
        <el-table-column prop="Extra" label="额外" />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePagination, PAGE_SIZE_OPTIONS } from '@/composables/usePagination'
import {
  getMysqlDatabasesManage,
  getMysqlTablesManage,
  updateMysqlDatabaseManage,
  updateMysqlTableManage,
  getMysqlTableDetail,
  type MysqlDatabaseManage,
  type MysqlTableManage
} from '@/api/manage'

const databases = ref<MysqlDatabaseManage[]>([])
const tables = ref<MysqlTableManage[]>([])
const tableDetail = ref<any[]>([])
const databaseRemarkCache = ref<Record<number, string>>({})
const tableRemarkCache = ref<Record<number, string>>({})

const databasePager = usePagination()
const tablePager = usePagination()

const loading = ref(false)
const tablesLoading = ref(false)
const detailLoading = ref(false)

const tablesVisible = ref(false)
const detailVisible = ref(false)
const currentDatabase = ref<string>('')
const tablesTitle = ref('')

const remarkPattern = /^[A-Za-z0-9_\u4e00-\u9fff]+$/

const displayName = (name: string, remark?: string | null) => {
  return remark && remark.trim() ? remark : name
}

const normalizeRemark = (value?: string | null) => {
  const trimmed = (value || '').trim()
  return trimmed ? trimmed : null
}

const isValidRemark = (value?: string | null) => {
  const trimmed = (value || '').trim()
  if (!trimmed) {
    return true
  }
  return remarkPattern.test(trimmed)
}

const resetDatabaseRemark = (row: MysqlDatabaseManage) => {
  row.remark = databaseRemarkCache.value[row.id] ?? ''
}

const resetTableRemark = (row: MysqlTableManage) => {
  row.remark = tableRemarkCache.value[row.id] ?? ''
}

const loadDatabases = async (refresh = false) => {
  loading.value = true
  const requestedPage = databasePager.page.value
  try {
    const response = await getMysqlDatabasesManage(
      refresh,
      true,
      databasePager.page.value,
      databasePager.pageSize.value
    )
    databasePager.setTotal(response.total || 0)
    if (databasePager.page.value !== requestedPage) {
      await loadDatabases(refresh)
      return
    }
    databases.value = response.items || []
    const nextCache: Record<number, string> = {}
    databases.value.forEach((item) => {
      nextCache[item.id] = item.remark || ''
    })
    databaseRemarkCache.value = nextCache
  } catch (error: any) {
    ElMessage.error(error.message || '加载数据库失败')
  } finally {
    loading.value = false
  }
}

const openTables = async (row: MysqlDatabaseManage) => {
  currentDatabase.value = row.name
  tablesTitle.value = `数据库: ${displayName(row.name, row.remark)}`
  tablePager.resetPage()
  tablesVisible.value = true
  await loadTables(false)
}

const loadTables = async (refresh = false) => {
  if (!currentDatabase.value) {
    return
  }
  tablesLoading.value = true
  const requestedPage = tablePager.page.value
  try {
    const response = await getMysqlTablesManage(
      currentDatabase.value,
      refresh,
      true,
      tablePager.page.value,
      tablePager.pageSize.value
    )
    tablePager.setTotal(response.total || 0)
    if (tablePager.page.value !== requestedPage) {
      await loadTables(refresh)
      return
    }
    tables.value = response.items || []
    const nextCache: Record<number, string> = {}
    tables.value.forEach((item) => {
      nextCache[item.id] = item.remark || ''
    })
    tableRemarkCache.value = nextCache
  } catch (error: any) {
    ElMessage.error(error.message || '加载数据表失败')
  } finally {
    tablesLoading.value = false
  }
}

const updateDatabaseRemark = async (row: MysqlDatabaseManage) => {
  if (!isValidRemark(row.remark)) {
    ElMessage.error('备注仅支持中文、字母、数字、下划线')
    resetDatabaseRemark(row)
    return
  }
  const normalized = normalizeRemark(row.remark)
  try {
    await updateMysqlDatabaseManage(row.id, { remark: normalized })
    row.remark = normalized || ''
    databaseRemarkCache.value[row.id] = row.remark || ''
    ElMessage.success('备注已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    resetDatabaseRemark(row)
  }
}

const toggleDatabase = async (row: MysqlDatabaseManage) => {
  try {
    await updateMysqlDatabaseManage(row.id, { enabled: row.enabled })
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    row.enabled = !row.enabled
  }
}

const updateTableRemark = async (row: MysqlTableManage) => {
  if (!isValidRemark(row.remark)) {
    ElMessage.error('备注仅支持中文、字母、数字、下划线')
    resetTableRemark(row)
    return
  }
  const normalized = normalizeRemark(row.remark)
  try {
    await updateMysqlTableManage(row.id, { remark: normalized })
    row.remark = normalized || ''
    tableRemarkCache.value[row.id] = row.remark || ''
    ElMessage.success('备注已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    resetTableRemark(row)
  }
}

const toggleTable = async (row: MysqlTableManage) => {
  try {
    await updateMysqlTableManage(row.id, { enabled: row.enabled })
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    row.enabled = !row.enabled
  }
}

const openTableDetail = async (row: MysqlTableManage) => {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const response = await getMysqlTableDetail(row.database, row.name)
    tableDetail.value = response.columns || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载表结构失败')
  } finally {
    detailLoading.value = false
  }
}

const handleDatabasePageChange = () => {
  loadDatabases(false)
}

const handleTablePageChange = () => {
  loadTables(false)
}

onMounted(() => {
  loadDatabases(false)
})
</script>

<style scoped>
.manage-section {
  padding: 8px 0;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.drawer-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.name-cell {
  display: flex;
  flex-direction: column;
}

.name-cell .primary {
  font-weight: 600;
}

.name-cell .secondary {
  color: #909399;
  font-size: 12px;
}
</style>
