#!/bin/bash
# BERT训练与部署工作流 - 快速启动脚本

set -e

# 配置
NAMESPACE="dev"
WORKFLOW_FILE="bert-training-and-deployment.yaml"
REGISTRY="192.168.68.95:31443"
IMAGE_REPO="ai-apps/intent-bert"
GIT_REPO="https://github.com/fyl080801/intent-bert.git"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数
print_header() {
    echo -e "${BLUE}=========================================="
    echo "$1"
    echo -e "==========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# 检查kubectl
print_header "1. 检查前置条件"

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl 未安装"
    exit 1
fi
print_success "kubectl 已安装"

if ! command -v argo &> /dev/null; then
    print_error "argo CLI 未安装"
    print_info "安装命令: brew install argo 或 visit https://argoproj.github.io/argo-workflows/"
    exit 1
fi
print_success "argo CLI 已安装"

# 检查命名空间
print_header "2. 检查命名空间"
if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    print_success "命名空间 $NAMESPACE 已存在"
else
    print_info "创建命名空间 $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
    print_success "命名空间 $NAMESPACE 创建成功"
fi

# 检查RuntimeClass
print_header "3. 检查RuntimeClass"
if kubectl get runtimeclass nvidia -n "$NAMESPACE" &> /dev/null; then
    print_success "RuntimeClass nvidia 已存在"
else
    print_info "创建RuntimeClass nvidia"
    kubectl apply -f - << EOF
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
  namespace: $NAMESPACE
handler: nvidia
EOF
    print_success "RuntimeClass nvidia 创建成功"
fi

# 检查PVC
print_header "4. 检查PVC"
PVC_EXISTS=$(kubectl get pvc bert-training-data-pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
if [ "$PVC_EXISTS" -eq 1 ]; then
    print_success "PVC bert-training-data-pvc 已存在"
else
    print_error "PVC bert-training-data-pvc 不存在"
    print_info "请先创建PVC或运行: kubectl apply -f k8s-supporting-resources.yaml"
    read -p "是否现在创建? (y/N): " CREATE_PVC
    if [[ $CREATE_PVC =~ ^[Yy]$ ]]; then
        # 只创建PVC部分
        kubectl apply -f - << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bert-training-data-pvc
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 10Gi
EOF
        print_success "PVC 创建成功"
        print_info "请上传训练数据到PVC"
    else
        print_error "未创建PVC，无法继续"
        exit 1
    fi
fi

# 检查Docker Registry Secret
print_header "5. 检查Docker Registry Secret"
if kubectl get secret docker-registry-secret -n "$NAMESPACE" &> /dev/null; then
    print_success "Secret docker-registry-secret 已存在"
else
    print_error "Secret docker-registry-secret 不存在"
    print_info "请创建Docker Registry Secret:"
    echo "kubectl create secret docker-registry docker-registry-secret \\"
    echo "  --docker-server=$REGISTRY \\"
    echo "  --docker-username=<your-username> \\"
    echo "  --docker-password=<your-password> \\"
    echo "  -n $NAMESPACE"
    read -p "是否现在创建? (y/N): " CREATE_SECRET
    if [[ $CREATE_SECRET =~ ^[Yy]$ ]]; then
        read -p "Docker用户名: " DOCKER_USERNAME
        read -sp "Docker密码: " DOCKER_PASSWORD
        echo ""
        kubectl create secret docker-registry docker-registry-secret \
          --docker-server="$REGISTRY" \
          --docker-username="$DOCKER_USERNAME" \
          --docker-password="$DOCKER_PASSWORD" \
          -n "$NAMESPACE"
        print_success "Secret 创建成功"
    else
        print_error "未创建Secret，工作流可能无法推送镜像"
    fi
fi

# 配置参数
print_header "6. 工作流参数配置"

echo ""
print_info "默认配置:"
echo "  Git仓库: $GIT_REPO"
echo "  命名空间: $NAMESPACE"
echo "  镜像仓库: $REGISTRY/$IMAGE_REPO"
echo "  代理: http://192.168.68.95:25041"
echo ""

read -p "是否使用默认配置? (Y/n): " USE_DEFAULT
if [[ ! $USE_DEFAULT =~ ^[Nn]$ ]]; then
    # 使用默认配置
    BRANCH="main"
    MODEL_NAME="hfl/chinese-roberta-wwm-ext"
    BATCH_SIZE="16"
    NUM_EPOCHS="5"
    LEARNING_RATE="2e-5"
    IMAGE_TAG="latest"
    HTTPS_PROXY="http://192.168.68.95:25041"
    HTTP_PROXY="http://192.168.68.95:25041"
else
    # 自定义配置
    read -p "Git分支 (默认: main): " BRANCH
    BRANCH=${BRANCH:-"main"}
    
    read -p "模型名称 (默认: bert-base-chinese): " MODEL_NAME
    MODEL_NAME=${MODEL_NAME:-"hfl/chinese-roberta-wwm-ext"}
    
    read -p "批次大小 (默认: 16): " BATCH_SIZE
    BATCH_SIZE=${BATCH_SIZE:-"16"}
    
    read -p "训练轮数 (默认: 5): " NUM_EPOCHS
    NUM_EPOCHS=${NUM_EPOCHS:-"5"}
    
    read -p "学习率 (默认: 2e-5): " LEARNING_RATE
    LEARNING_RATE=${LEARNING_RATE:-"2e-5"}
    
    read -p "镜像标签 (默认: latest): " IMAGE_TAG
    IMAGE_TAG=${IMAGE_TAG:-"latest"}

    read -p "HTTPS代理 (默认: http://192.168.68.95:25041): " HTTPS_PROXY
    HTTPS_PROXY=${HTTPS_PROXY:-"http://192.168.68.95:25041"}

    read -p "HTTP代理 (默认: http://192.168.68.95:25041): " HTTP_PROXY
    HTTP_PROXY=${HTTP_PROXY:-"http://192.168.68.95:25041"}
fi

# 提交工作流
print_header "7. 提交工作流"

WORKFLOW_NAME="bert-training-$(date +%Y%m%d-%H%M%S)"
print_info "工作流名称: $WORKFLOW_NAME"
print_info "配置参数:"
echo "  Git仓库: $GIT_REPO"
echo "  Git分支: $BRANCH"
echo "  模型名称: $MODEL_NAME"
echo "  批次大小: $BATCH_SIZE"
echo "  训练轮数: $NUM_EPOCHS"
echo "  学习率: $LEARNING_RATE"
echo "  镜像标签: $IMAGE_TAG"
echo "  HTTPS代理: $HTTPS_PROXY"
echo "  HTTP代理: $HTTP_PROXY"
echo ""

read -p "确认提交工作流? (Y/n): " CONFIRM
if [[ $CONFIRM =~ ^[Nn]$ ]]; then
    print_info "已取消"
    exit 0
fi

print_info "提交工作流..."
argo submit "$WORKFLOW_FILE" \
  --namespace "$NAMESPACE" \
  --name "$WORKFLOW_NAME" \
  -p repo_url="$GIT_REPO" \
  -p branch="$BRANCH" \
  -p model_name="$MODEL_NAME" \
  -p batch_size="$BATCH_SIZE" \
  -p num_epochs="$NUM_EPOCHS" \
  -p learning_rate="$LEARNING_RATE" \
  -p image_registry="$REGISTRY" \
  -p image_repository="$IMAGE_REPO" \
  -p image_tag="$IMAGE_TAG" \
  -p https_proxy="$HTTPS_PROXY" \
  -p http_proxy="$HTTP_PROXY" \
  --watch

# 显示后续命令
print_header "8. 后续操作"
echo ""
echo "监控工作流:"
echo "  argo get $WORKFLOW_NAME -n $NAMESPACE"
echo "  argo watch $WORKFLOW_NAME -n $NAMESPACE"
echo "  argo logs $WORKFLOW_NAME -n $NAMESPACE"
echo ""
echo "查看Pod:"
echo "  kubectl get pods -n $NAMESPACE -l workflows.argoproj.io/workflow=$WORKFLOW_NAME"
echo ""
echo "Argo UI:"
echo "  kubectl port-forward -n argo svc/argo-server 2746:2746"
echo "  open http://localhost:2746"
echo ""
print_success "工作流已提交！"
