import request from './request';
import type { ApiResponse, User, AuthTokens, LoginForm, RegisterForm } from '@/types';

export const authApi = {
  login: (data: LoginForm) =>
    request.post<unknown, ApiResponse<{ user: User } & AuthTokens>>('/auth/login', data),

  register: (data: RegisterForm) =>
    request.post<unknown, ApiResponse<{ user: User } & AuthTokens>>('/auth/register', data),

  logout: () =>
    request.post<unknown, ApiResponse>('/auth/logout'),

  getProfile: () =>
    request.get<unknown, ApiResponse<User>>('/auth/profile'),

  changePassword: (data: { currentPassword: string; newPassword: string }) =>
    request.put<unknown, ApiResponse>('/auth/change-password', data),

  refreshToken: (refreshToken: string) =>
    request.post<unknown, ApiResponse<AuthTokens>>('/auth/refresh-token', { refreshToken }),
};
