import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib

# 设置中文字体 (尝试几种常见的系统字体)
plt.rcParams['font.sans-serif'] = ['SimHei', 'SimSun', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def create_architecture_diagram():
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # 定义绘制带文本框的函数
    def draw_box(x, y, w, h, text, color='#E3F2FD', edgecolor='#1976D2'):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", 
                                     linewidth=2, edgecolor=edgecolor, facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=11, fontweight='bold')

    # 1. 用户浏览器层
    draw_box(1, 7.5, 8, 2, "用户浏览器 (Web Browser)", color='#E1F5FE', edgecolor='#0288D1')
    draw_box(1.5, 8, 3, 1, "用户前端界面\n(查询系统)", color='#B3E5FC', edgecolor='#039BE5')
    draw_box(5.5, 8, 3, 1, "管理后台界面\n(数据/用户管理)", color='#B3E5FC', edgecolor='#039BE5')

    # 2. 后端服务层
    draw_box(1, 4, 8, 2, "FastAPI 后端核心服务", color='#E8F5E9', edgecolor='#388E3C')
    # 内部模块
    draw_box(1.3, 4.4, 1.8, 0.8, "认证模块\n(JWT/TOTP)", color='#C8E6C9', edgecolor='#43A047')
    draw_box(3.3, 4.4, 1.8, 0.8, "数据模块\n(CRUD/查询)", color='#C8E6C9', edgecolor='#43A047')
    draw_box(5.3, 4.4, 1.8, 0.8, "安全模块\n(限流/审计)", color='#C8E6C9', edgecolor='#43A047')
    draw_box(7.3, 4.4, 1.8, 0.8, "备份模块\n(SQL/Restore)", color='#C8E6C9', edgecolor='#43A047')

    # 3. 数据库层
    draw_box(1.5, 0.8, 3, 1.5, "gas_data.db\n(气体平衡数据库)", color='#FFF9C4', edgecolor='#FBC02D')
    draw_box(5.5, 0.8, 3, 1.5, "security.db\n(用户信息与日志)", color='#FFF9C4', edgecolor='#FBC02D')

    # 绘制连接箭头
    # 浏览器 <-> 后端
    ax.annotate('', xy=(3, 7.4), xytext=(3, 6.1), arrowprops=dict(arrowstyle='<->', color='#546E7A', lw=2))
    ax.annotate('', xy=(7, 7.4), xytext=(7, 6.1), arrowprops=dict(arrowstyle='<->', color='#546E7A', lw=2))
    ax.text(5, 6.7, "HTTP / REST API (JSON)", ha='center', fontsize=10, style='italic', color='#455A64')

    # 后端 -> 数据库
    ax.annotate('', xy=(3, 3.9), xytext=(3, 2.4), arrowprops=dict(arrowstyle='->', color='#546E7A', lw=2))
    ax.annotate('', xy=(7, 3.9), xytext=(7, 2.4), arrowprops=dict(arrowstyle='->', color='#546E7A', lw=2))
    ax.text(5, 3.1, "SQL Queries (SQLite/MySQL)", ha='center', fontsize=10, style='italic', color='#455A64')

    # 保存图片
    plt.tight_layout()
    plt.savefig('docs/architecture.png', dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    create_architecture_diagram()
