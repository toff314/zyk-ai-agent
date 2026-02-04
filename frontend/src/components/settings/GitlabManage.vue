<template>
  <div class="manage-section">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="项目" name="projects">
        <div class="toolbar">
          <el-button type="primary" @click="loadProjects()">刷新</el-button>
        </div>
        <el-table :data="projects" v-loading="projectsLoading" row-key="id">
          <el-table-column label="项目" min-width="220">
            <template #default="scope">
              <div class="name-cell">
                <div class="primary">{{ displayName(scope.row.path_with_namespace || scope.row.name, scope.row.remark) }}</div>
                <div class="secondary">{{ scope.row.path_with_namespace || scope.row.name }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="branch_count" label="分支数" width="100" />
          <el-table-column label="启用" width="100">
            <template #default="scope">
              <el-switch v-model="scope.row.enabled" @change="toggleProject(scope.row)" />
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="180">
            <template #default="scope">
              <el-input v-model="scope.row.remark" placeholder="备注" @blur="updateProjectRemark(scope.row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="scope">
              <el-button size="small" @click="openBranches(scope.row)">查看分支</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination
            v-model:current-page="projectPager.page"
            v-model:page-size="projectPager.pageSize"
            :page-sizes="PAGE_SIZE_OPTIONS"
            :total="projectPager.total"
            layout="total, sizes, prev, pager, next"
            @size-change="handleProjectPageChange"
            @current-change="handleProjectPageChange"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="用户" name="users">
        <div class="toolbar">
          <el-button type="primary" @click="loadUsers()">刷新</el-button>
        </div>
        <el-table :data="users" v-loading="usersLoading" row-key="id">
          <el-table-column label="用户" min-width="220">
            <template #default="scope">
              <div class="name-cell">
                <div class="primary">{{ displayName(scope.row.name || scope.row.username, scope.row.remark) }}</div>
                <div class="secondary">{{ scope.row.username }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="commits_week" label="本周提交" width="120" />
          <el-table-column label="启用" width="100">
            <template #default="scope">
              <el-switch v-model="scope.row.enabled" @change="toggleUser(scope.row)" />
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="180">
            <template #default="scope">
              <el-input v-model="scope.row.remark" placeholder="备注" @blur="updateUserRemark(scope.row)" />
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination
            v-model:current-page="userPager.page"
            v-model:page-size="userPager.pageSize"
            :page-sizes="PAGE_SIZE_OPTIONS"
            :total="userPager.total"
            layout="total, sizes, prev, pager, next"
            @size-change="handleUserPageChange"
            @current-change="handleUserPageChange"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="branchesVisible" :title="branchesTitle" size="60%">
      <div class="drawer-toolbar">
        <el-button type="primary" @click="loadBranches(true)">刷新</el-button>
      </div>
      <el-table :data="branches" v-loading="branchesLoading">
        <el-table-column prop="name" label="分支" min-width="200" />
        <el-table-column prop="commit_sha" label="提交" min-width="200" />
        <el-table-column prop="committed_date" label="提交时间" min-width="160" />
        <el-table-column label="操作" width="140">
          <template #default="scope">
            <el-button size="small" @click="openCommits(scope.row)">查看提交</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          v-model:current-page="branchPager.page"
          v-model:page-size="branchPager.pageSize"
          :page-sizes="PAGE_SIZE_OPTIONS"
          :total="branchPager.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleBranchPageChange"
          @current-change="handleBranchPageChange"
        />
      </div>
    </el-drawer>

    <el-drawer v-model="commitsVisible" :title="commitsTitle" size="70%">
      <div class="drawer-toolbar">
        <el-button type="primary" @click="loadCommits(true)">刷新</el-button>
      </div>
      <el-table :data="commits" v-loading="commitsLoading">
        <el-table-column prop="commit_sha" label="提交ID" min-width="200" />
        <el-table-column prop="title" label="标题" min-width="240" />
        <el-table-column prop="author_name" label="作者" width="140" />
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column label="操作" width="140">
          <template #default="scope">
            <el-button size="small" @click="openDiffs(scope.row)">查看diff</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          v-model:current-page="commitPager.page"
          v-model:page-size="commitPager.pageSize"
          :page-sizes="PAGE_SIZE_OPTIONS"
          :total="commitPager.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleCommitPageChange"
          @current-change="handleCommitPageChange"
        />
      </div>
    </el-drawer>

    <el-drawer v-model="diffsVisible" :title="diffsTitle" size="70%">
      <div class="diff-list">
        <el-collapse>
          <el-collapse-item v-for="(diff, idx) in diffs" :key="idx" :title="diff.new_path || diff.old_path">
            <pre class="diff-text">{{ diff.diff }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePagination, PAGE_SIZE_OPTIONS } from '@/composables/usePagination'
import {
  getGitlabProjects,
  updateGitlabProject,
  getGitlabUsers,
  updateGitlabUser,
  getGitlabBranches,
  getGitlabCommits,
  getGitlabCommitDiffs,
  type GitlabProjectManage,
  type GitlabUserManage,
  type GitlabBranch,
  type GitlabCommit,
  type GitlabCommitDiff
} from '@/api/manage'

const activeTab = ref('projects')

const projects = ref<GitlabProjectManage[]>([])
const users = ref<GitlabUserManage[]>([])
const branches = ref<GitlabBranch[]>([])
const commits = ref<GitlabCommit[]>([])
const diffs = ref<GitlabCommitDiff[]>([])
const projectRemarkCache = ref<Record<number, string>>({})
const userRemarkCache = ref<Record<number, string>>({})

const projectPager = usePagination()
const userPager = usePagination()
const branchPager = usePagination()
const commitPager = usePagination()

const projectsLoading = ref(false)
const usersLoading = ref(false)
const branchesLoading = ref(false)
const commitsLoading = ref(false)

const branchesVisible = ref(false)
const commitsVisible = ref(false)
const diffsVisible = ref(false)

const currentProject = ref<GitlabProjectManage | null>(null)
const currentBranch = ref<GitlabBranch | null>(null)
const currentCommit = ref<GitlabCommit | null>(null)

const branchesTitle = ref('')
const commitsTitle = ref('')
const diffsTitle = ref('')

const remarkPattern = /^[A-Za-z0-9_\u4e00-\u9fff]+$/

const displayName = (name?: string, remark?: string | null) => {
  if (remark && remark.trim()) {
    return remark
  }
  return name || ''
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

const resetProjectRemark = (row: GitlabProjectManage) => {
  row.remark = projectRemarkCache.value[row.id] ?? ''
}

const resetUserRemark = (row: GitlabUserManage) => {
  row.remark = userRemarkCache.value[row.id] ?? ''
}

const loadProjects = async () => {
  projectsLoading.value = true
  const requestedPage = projectPager.page.value
  try {
    const response = await getGitlabProjects(
      true,
      projectPager.page.value,
      projectPager.pageSize.value
    )
    projectPager.setTotal(response.total || 0)
    if (projectPager.page.value !== requestedPage) {
      await loadProjects()
      return
    }
    projects.value = response.items || []
    const nextCache: Record<number, string> = {}
    projects.value.forEach((item) => {
      nextCache[item.id] = item.remark || ''
    })
    projectRemarkCache.value = nextCache
  } catch (error: any) {
    ElMessage.error(error.message || '加载项目失败')
  } finally {
    projectsLoading.value = false
  }
}

const loadUsers = async () => {
  usersLoading.value = true
  const requestedPage = userPager.page.value
  try {
    const response = await getGitlabUsers(true, userPager.page.value, userPager.pageSize.value)
    userPager.setTotal(response.total || 0)
    if (userPager.page.value !== requestedPage) {
      await loadUsers()
      return
    }
    users.value = response.items || []
    const nextCache: Record<number, string> = {}
    users.value.forEach((item) => {
      nextCache[item.id] = item.remark || ''
    })
    userRemarkCache.value = nextCache
  } catch (error: any) {
    ElMessage.error(error.message || '加载用户失败')
  } finally {
    usersLoading.value = false
  }
}

const toggleProject = async (row: GitlabProjectManage) => {
  try {
    await updateGitlabProject(row.id, { enabled: row.enabled })
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    row.enabled = !row.enabled
  }
}

const updateProjectRemark = async (row: GitlabProjectManage) => {
  if (!isValidRemark(row.remark)) {
    ElMessage.error('备注仅支持中文、字母、数字、下划线')
    resetProjectRemark(row)
    return
  }
  const normalized = normalizeRemark(row.remark)
  try {
    await updateGitlabProject(row.id, { remark: normalized })
    row.remark = normalized || ''
    projectRemarkCache.value[row.id] = row.remark || ''
    ElMessage.success('备注已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    resetProjectRemark(row)
  }
}

const toggleUser = async (row: GitlabUserManage) => {
  try {
    await updateGitlabUser(row.id, { enabled: row.enabled })
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    row.enabled = !row.enabled
  }
}

const updateUserRemark = async (row: GitlabUserManage) => {
  if (!isValidRemark(row.remark)) {
    ElMessage.error('备注仅支持中文、字母、数字、下划线')
    resetUserRemark(row)
    return
  }
  const normalized = normalizeRemark(row.remark)
  try {
    await updateGitlabUser(row.id, { remark: normalized })
    row.remark = normalized || ''
    userRemarkCache.value[row.id] = row.remark || ''
    ElMessage.success('备注已更新')
  } catch (error: any) {
    ElMessage.error(error.message || '更新失败')
    resetUserRemark(row)
  }
}

const openBranches = async (row: GitlabProjectManage) => {
  currentProject.value = row
  branchesTitle.value = `项目: ${displayName(row.path_with_namespace || row.name, row.remark)}`
  branchPager.resetPage()
  branchesVisible.value = true
  await loadBranches(false)
}

const loadBranches = async (refresh = false) => {
  if (!currentProject.value) return
  branchesLoading.value = true
  const requestedPage = branchPager.page.value
  try {
    const response = await getGitlabBranches(
      currentProject.value.id,
      refresh,
      branchPager.page.value,
      branchPager.pageSize.value
    )
    branchPager.setTotal(response.total || 0)
    if (branchPager.page.value !== requestedPage) {
      await loadBranches(refresh)
      return
    }
    branches.value = response.items || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载分支失败')
  } finally {
    branchesLoading.value = false
  }
}

const openCommits = async (branch: GitlabBranch) => {
  currentBranch.value = branch
  commitsTitle.value = `分支: ${branch.name}`
  commitPager.resetPage()
  commitsVisible.value = true
  await loadCommits(false)
}

const loadCommits = async (refresh = false) => {
  if (!currentProject.value || !currentBranch.value) return
  commitsLoading.value = true
  const requestedPage = commitPager.page.value
  try {
    const response = await getGitlabCommits(
      currentProject.value.id,
      currentBranch.value.name,
      refresh,
      50,
      commitPager.page.value,
      commitPager.pageSize.value
    )
    commitPager.setTotal(response.total || 0)
    if (commitPager.page.value !== requestedPage) {
      await loadCommits(refresh)
      return
    }
    commits.value = response.items || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载提交失败')
  } finally {
    commitsLoading.value = false
  }
}

const openDiffs = async (commit: GitlabCommit) => {
  currentCommit.value = commit
  diffsTitle.value = `提交: ${commit.commit_sha}`
  diffsVisible.value = true
  try {
    diffs.value = await getGitlabCommitDiffs(currentProject.value!.id, commit.commit_sha, true)
  } catch (error: any) {
    ElMessage.error(error.message || '加载Diff失败')
  }
}

const handleProjectPageChange = () => {
  loadProjects()
}

const handleUserPageChange = () => {
  loadUsers()
}

const handleBranchPageChange = () => {
  loadBranches(false)
}

const handleCommitPageChange = () => {
  loadCommits(false)
}

onMounted(() => {
  loadProjects()
  loadUsers()
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

.diff-text {
  white-space: pre-wrap;
  font-family: "Courier New", monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
}
</style>
