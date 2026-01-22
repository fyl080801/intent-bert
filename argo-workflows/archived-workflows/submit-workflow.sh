#!/bin/bash
# Argo Workflow 提交脚本
# 用于快速提交 BERT 微调工作流

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
NAMESPACE="default"
WORKFLOW_FILE="bert-finetune-simple.yaml"
IMAGE_REGISTRY="registry.example.com"
IMAGE_NAME="bert-finetune"
IMAGE_TAG="latest"

# 训练参数默认值
TRAIN_DATA_PATH="datasets/financial_intent_dataset.csv"
VAL_DATA_PATH="datasets/financial_intent_validation.csv"
MODEL_NAME="hfl/chinese-roberta-wwm-ext"
BATCH_SIZE=16
NUM_EPOCHS=5
LEARNING_RATE="2e-5"
HOST_MODEL_PATH="/mnt/models/bert-finetune"

# 函数：打印帮助信息
usage() {
    cat << EOF
用法: $0 [选项]

提交 BERT 微调 Argo Workflow

选项:
    -n, --namespace <namespace>        Kubernetes 命名空间 (默认: default)
    -f, --file <workflow-file>         Workflow 文件 (默认: bert-finetune-simple.yaml)
    --full                             使用完整版 workflow (bert-finetune-workflow.yaml)
    --train-data <path>                训练数据路径 (默认: datasets/financial_intent_dataset.csv)
    --val-data <path>                  验证数据路径 (默认: datasets/financial_intent_validation.csv)
    --model <name>                     预训练模型名称 (默认: bert-base-chinese)
    --batch-size <size>                批次大小 (默认: 16)
    --epochs <num>                     训练轮数 (默认: 5)
    --learning-rate <rate>             学习率 (默认: 2e-5)
    --host-path <path>                 Node 本地模型存储路径 (默认: /mnt/models/bert-finetune)
    --image <registry/image:tag>       Docker 镜像 (默认: registry.example.com/bert-finetune:latest)
    -w, --watch                        实时监控工作流
    -l, --logs                         查看工作流日志
    -h, --help                         显示此帮助信息

示例:
    # 使用默认参数提交
    $0

    # 提交并实时监控
    $0 --watch

    # 使用完整版 workflow
    $0 --full --watch

    # 自定义训练参数
    $0 --batch-size 32 --epochs 10 --learning-rate 3e-5

    # 指定命名空间和镜像
    $0 -n bert-prod --image my-registry.com/bert:v1.0

EOF
    exit 0
}

# 函数：打印信息
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# 函数：检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "$1 未安装，请先安装 $1"
    fi
}

# 函数：检查 Argo CLI
check_argo() {
    check_command argo

    # 检查 argo 是否配置正确
    if ! argo version &> /dev/null; then
        error "Argo CLI 配置不正确，请检查 KUBECONFIG 和 Argo 服务器连接"
    fi

    info "Argo CLI 版本: $(argo version --short | head -n1)"
}

# 函数：检查 kubectl
check_kubectl() {
    check_command kubectl

    # 检查集群连接
    if ! kubectl cluster-info &> /dev/null; then
        error "无法连接到 Kubernetes 集群"
    fi

    info "Kubernetes 集群: $(kubectl config current-context)"
}

# 函数：验证工作流文件
validate_workflow_file() {
    if [ ! -f "$WORKFLOW_FILE" ]; then
        error "Workflow 文件不存在: $WORKFLOW_FILE"
    fi

    info "使用 Workflow 文件: $WORKFLOW_FILE"
}

# 函数：验证 hostPath
validate_hostpath() {
    info "验证 hostPath: $HOST_MODEL_PATH"

    # 检查是否能在节点上创建目录
    warn "请确保所有 Kubernetes 节点上存在目录: $HOST_MODEL_PATH"
    warn "运行以下命令在节点上创建目录:"
    warn "  sudo mkdir -p $HOST_MODEL_PATH"
    warn "  sudo chmod 755 $HOST_MODEL_PATH"
}

# 函数：构建工作流名称
build_workflow_name() {
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    WORKFLOW_NAME="bert-finetune-${TIMESTAMP}"
}

# 函数：提交工作流
submit_workflow() {
    info "准备提交工作流..."
    info "工作流名称: $WORKFLOW_NAME"
    info "命名空间: $NAMESPACE"

    # 构建参数
    ARGS="-p train_data_path=${TRAIN_DATA_PATH}"
    ARGS="${ARGS} -p val_data_path=${VAL_DATA_PATH}"
    ARGS="${ARGS} -p model_name=${MODEL_NAME}"
    ARGS="${ARGS} -p batch_size=${BATCH_SIZE}"
    ARGS="${ARGS} -p num_epochs=${NUM_EPOCHS}"
    ARGS="${ARGS} -p learning_rate=${LEARNING_RATE}"
    ARGS="${ARGS} -p host_model_path=${HOST_MODEL_PATH}"

    info "训练参数:"
    info "  - 批次大小: ${BATCH_SIZE}"
    info "  - 训练轮数: ${NUM_EPOCHS}"
    info "  - 学习率: ${LEARNING_RATE}"
    info "  - 模型: ${MODEL_NAME}"
    info "  - hostPath: ${HOST_MODEL_PATH}"

    # 提交工作流
    info "提交工作流..."
    argo submit ${WORKFLOW_FILE} \
        --name ${WORKFLOW_NAME} \
        --namespace ${NAMESPACE} \
        ${ARGS} \
        --labels "app=bert-finetune,project=financial-intent-classification" \
        --annotations "description=BERT fine-tuning workflow"

    if [ $? -eq 0 ]; then
        info "工作流提交成功！"
        echo ""
        info "查看工作流状态:"
        echo "  argo get ${WORKFLOW_NAME} -n ${NAMESPACE}"
        echo ""
        info "查看工作流日志:"
        echo "  argo logs ${WORKFLOW_NAME} -n ${NAMESPACE}"
        echo ""
        info "实时监控工作流:"
        echo "  argo watch ${WORKFLOW_NAME} -n ${NAMESPACE}"
    else
        error "工作流提交失败"
    fi
}

# 函数：监控工作流
watch_workflow() {
    info "监控工作流: ${WORKFLOW_NAME}"
    argo watch ${WORKFLOW_NAME} -n ${NAMESPACE}
}

# 函数：查看日志
show_logs() {
    info "查看工作流日志: ${WORKFLOW_NAME}"
    argo logs ${WORKFLOW_NAME} -n ${NAMESPACE} -f
}

# 解析命令行参数
WATCH=false
SHOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -f|--file)
            WORKFLOW_FILE="$2"
            shift 2
            ;;
        --full)
            WORKFLOW_FILE="bert-finetune-workflow.yaml"
            shift
            ;;
        --train-data)
            TRAIN_DATA_PATH="$2"
            shift 2
            ;;
        --val-data)
            VAL_DATA_PATH="$2"
            shift 2
            ;;
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --epochs)
            NUM_EPOCHS="$2"
            shift 2
            ;;
        --learning-rate)
            LEARNING_RATE="$2"
            shift 2
            ;;
        --host-path)
            HOST_MODEL_PATH="$2"
            shift 2
            ;;
        --image)
            IMAGE="$2"
            shift 2
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "未知选项: $1"
            ;;
    esac
done

# 主流程
main() {
    echo ""
    echo "=========================================="
    echo "  BERT 微调 Argo Workflow 提交工具"
    echo "=========================================="
    echo ""

    # 检查依赖
    check_argo
    check_kubectl

    # 验证配置
    validate_workflow_file
    validate_hostpath

    # 构建工作流名称
    build_workflow_name

    # 提交工作流
    submit_workflow

    # 监控或查看日志
    if [ "$WATCH" = true ]; then
        echo ""
        watch_workflow
    elif [ "$SHOW_LOGS" = true ]; then
        echo ""
        show_logs
    fi
}

# 执行主流程
main
