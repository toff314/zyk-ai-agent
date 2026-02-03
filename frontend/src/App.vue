<template>
  <div class="app-shell">
    <header v-if="showNav" class="app-header">
      <div class="brand" @click="go('/')">CSPM数据运营AI平台</div>
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        class="nav-menu"
        router
      >
        <el-menu-item index="/">对话</el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/users">用户管理</el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/settings">配置管理</el-menu-item>
      </el-menu>
      <div class="header-actions">
        <el-dropdown v-if="userStore.user">
          <span class="username">
            {{ userStore.user.username }}
            <el-tag v-if="userStore.user.role === 'admin'" size="small" type="warning">管理员</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="userStore.isAdmin" @click="go('/users')">用户管理</el-dropdown-item>
              <el-dropdown-item v-if="userStore.isAdmin" @click="go('/settings')">配置管理</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-else type="primary" size="small" @click="go('/login')">登录</el-button>
      </div>
    </header>
    <main class="app-main" :class="{ 'without-nav': !showNav }">
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const showNav = computed(() => !route.meta.hideNav)
const activeMenu = computed(() => route.path)

const go = (path: string) => {
  router.push(path)
}

const handleLogout = async () => {
  await userStore.logout()
  ElMessage.success('已退出登录')
  if (route.path !== '/login') {
    router.push('/login')
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100vh;
  width: 100vw;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.app-header {
  height: 56px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand {
  font-weight: 600;
  color: #303133;
  cursor: pointer;
  white-space: nowrap;
}

.nav-menu {
  flex: 1;
  border-bottom: none;
}

.nav-menu.el-menu--horizontal {
  border-bottom: none;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  cursor: pointer;
}

.app-main {
  flex: 1;
  min-height: 0;
}
</style>
