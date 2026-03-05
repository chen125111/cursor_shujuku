import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

request.interceptors.response.use(
  (response) => response.data,
  async (error: AxiosError<{ message: string }>) => {
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401: {
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken && error.config) {
            try {
              const res = await axios.post(
                `${import.meta.env.VITE_API_BASE_URL}/auth/refresh-token`,
                { refreshToken }
              );
              const { accessToken, refreshToken: newRefreshToken } = res.data.data;
              localStorage.setItem('access_token', accessToken);
              localStorage.setItem('refresh_token', newRefreshToken);
              error.config.headers.Authorization = `Bearer ${accessToken}`;
              return request(error.config);
            } catch {
              localStorage.clear();
              window.location.href = '/login';
            }
          } else {
            localStorage.clear();
            window.location.href = '/login';
          }
          break;
        }
        case 403:
          message.error('权限不足');
          break;
        case 404:
          message.error('资源不存在');
          break;
        case 429:
          message.error('请求过于频繁，请稍后再试');
          break;
        default:
          message.error(data?.message || '服务器错误');
      }
    } else if (error.request) {
      message.error('网络连接异常，请检查网络');
    }
    return Promise.reject(error);
  }
);

export default request;
