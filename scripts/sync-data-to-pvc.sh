#!/bin/bash
#
# 将本地数据集同步到 Kubernetes PVC 存储卷
# 用于将新创建/修改的数据集上传到集群供训练使用
#

set -e

# 配置
NAMESPACE=${NAMESPACE:-"dev"}
PVC_NAME=${PVC_NAME:-"bert-training-data-pvc"}
MOUNT_PATH=${MOUNT_PATH:-"/data"}
TEMP_POD="data-sync-pod-$$"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 kubectl
if ! command -v kubectl &> /dev/null; then
    echo_error "kubectl 未找到，请先安装 kubectl"
    exit 1
fi

# 检查 PVC 是否存在
echo_info "检查 PVC 状态..."
if ! kubectl get pvc "$PVC_NAME" -n "$NAMESPACE" &> /dev/null; then
    echo_error "PVC '$PVC_NAME' 在命名空间 '$NAMESPACE' 中不存在"
    exit 1
fi

PVC_STATUS=$(kubectl get pvc "$PVC_NAME" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
echo_info "PVC 状态: $PVC_STATUS"

# 清理函数
cleanup() {
    echo_info "清理临时 Pod..."
    kubectl delete pod "$TEMP_POD" -n "$NAMESPACE" --ignore-not-found=true &> /dev/null || true
}

# 设置退出时清理
trap cleanup EXIT

# 创建临时 Pod
echo_info "创建临时同步 Pod..."
kubectl run "$TEMP_POD" \
  --namespace "$NAMESPACE" \
  --restart=Never \
  --image=busybox:1.36 \
  --overrides="
{
  \"spec\": {
    \"containers\": [{
      \"name\": \"$TEMP_POD\",
      \"image\": \"busybox:1.36\",
      \"command\": [\"sh\", \"-c\", \"sleep 3600\"],
      \"volumeMounts\": [{
        \"name\": \"data\",
        \"mountPath\": \"$MOUNT_PATH\"
      }]
    }],
    \"volumes\": [{
      \"name\": \"data\",
      \"persistentVolumeClaim\": {
        \"claimName\": \"$PVC_NAME\"
      }
    }]
  }
}" &> /dev/null

# 等待 Pod 就绪
echo_info "等待 Pod 启动..."
for i in {1..30}; do
    POD_STATUS=$(kubectl get pod "$TEMP_POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
    if [ "$POD_STATUS" == "Running" ]; then
        echo_info "Pod 已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo_error "Pod 启动超时"
        exit 1
    fi
    echo_info "等待中... ($i/30)"
    sleep 2
done

# 同步文件
echo_info "开始同步文件..."

# 获取所有要同步的文件/目录
SYNC_ITEMS=("$@")

if [ ${#SYNC_ITEMS[@]} -eq 0 ]; then
    # 默认同步增量训练数据集
    echo_warn "未指定文件，同步默认的增量训练数据集..."
    SYNC_ITEMS=(
        "datasets/financial_intent_incremental_v1"
        "datasets/financial_intent_incremental_v2"
        "datasets/dataset_registry.json"
        "datasets/financial_intent_fixed"
    )
fi

# 遍历并同步每个文件/目录
for ITEM in "${SYNC_ITEMS[@]}"; do
    if [ ! -e "$ITEM" ]; then
        echo_warn "跳过不存在的文件/目录: $ITEM"
        continue
    fi

    echo_info "同步: $ITEM"

    # 获取目标路径
    TARGET_PATH="$MOUNT_PATH/$ITEM"

    # 创建目标目录
    kubectl exec -n "$NAMESPACE" "$TEMP_POD" -- mkdir -p "$TARGET_PATH" &> /dev/null || true

    if [ -f "$ITEM" ]; then
        # 同步单个文件
        kubectl cp "$ITEM" "$NAMESPACE/$TEMP_POD:$TARGET_PATH"
        echo_info "  ✓ 文件已同步"
    elif [ -d "$ITEM" ]; then
        # 同步目录（使用 tar）
        cd "$(dirname "$ITEM")"
        DIR_NAME=$(basename "$ITEM")

        # 在容器中解压
        kubectl exec -n "$NAMESPACE" "$TEMP_POD" -- sh -c "cd $MOUNT_PATH && rm -rf ${TARGET_PATH}.tmp" 2>/dev/null || true

        # 使用 tar 传输
        tar czf - "$DIR_NAME" | kubectl exec -i -n "$NAMESPACE" "$TEMP_POD" -- sh -c "cd $MOUNT_PATH && tar xzf -"

        echo_info "  ✓ 目录已同步 ($(tar czf - "$DIR_NAME" 2>/dev/null | wc -c | awk '{printf "%.2f KB", $1/1024}')"
    fi
done

echo_info ""
echo_info "=========================================="
echo_info "数据同步完成！"
echo_info "=========================================="
echo_info "PVC: $PVC_NAME"
echo_info "命名空间: $NAMESPACE"
echo_info "挂载路径: $MOUNT_PATH"
echo_info ""

# 显示 PVC 中已同步的数据
echo_info "PVC 中的数据集："
kubectl exec -n "$NAMESPACE" "$TEMP_POD" -- ls -lh "$MOUNT_PATH/datasets/" 2>/dev/null || echo_warn "无法列出目录"

echo_info ""
echo_info "现在可以使用这些数据集进行训练了！"
