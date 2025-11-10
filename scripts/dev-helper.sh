#!/bin/bash

# Development Helper Script
# Quick commands for managing dev/prod environments

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

show_usage() {
    echo ""
    echo -e "${BLUE}Development Helper Commands${NC}"
    echo ""
    echo "Usage: bash scripts/dev-helper.sh <command>"
    echo ""
    echo "Commands:"
    echo ""
    echo "  status          - Show status of all services"
    echo "  restart-dev     - Restart development service (port 8081)"
    echo "  restart-prod    - Restart production service (port 8080)"
    echo "  logs-dev        - View development logs"
    echo "  logs-prod       - View production logs"
    echo "  test            - Test both services"
    echo "  start-dev       - Start development service"
    echo "  stop-dev        - Stop development service"
    echo "  new-feature     - Create new feature branch"
    echo "  list-branches   - List all Git branches"
    echo "  current-branch  - Show current Git branch"
    echo ""
    echo "Examples:"
    echo "  bash scripts/dev-helper.sh restart-dev"
    echo "  bash scripts/dev-helper.sh logs-dev"
    echo "  bash scripts/dev-helper.sh new-feature polygon-selection"
    echo ""
}

if [ $# -eq 0 ]; then
    show_usage
    exit 0
fi

COMMAND=$1

case $COMMAND in
    status)
        echo -e "${BLUE}Service Status:${NC}"
        echo ""
        echo -e "${YELLOW}Production (port 8080):${NC}"
        systemctl is-active swath-movers.service >/dev/null 2>&1 && echo -e "  ${GREEN}✓ Running${NC}" || echo -e "  ${RED}✗ Stopped${NC}"
        echo ""
        echo -e "${YELLOW}Development (port 8081):${NC}"
        systemctl is-active swath-movers-dev.service >/dev/null 2>&1 && echo -e "  ${GREEN}✓ Running${NC}" || echo -e "  ${RED}✗ Stopped${NC}"
        echo ""
        echo -e "${YELLOW}Cloudflare Tunnel:${NC}"
        systemctl is-active cloudflared.service >/dev/null 2>&1 && echo -e "  ${GREEN}✓ Running${NC}" || echo -e "  ${RED}✗ Stopped${NC}"
        echo ""
        echo -e "${YELLOW}Current Git Branch:${NC}"
        echo "  $(git branch --show-current)"
        echo ""
        ;;

    restart-dev)
        echo -e "${YELLOW}Restarting development service...${NC}"
        sudo systemctl restart swath-movers-dev
        sleep 2
        if systemctl is-active --quiet swath-movers-dev.service; then
            echo -e "${GREEN}✓ Development service restarted${NC}"
            echo ""
            echo "Test at: http://localhost:8081"
        else
            echo -e "${RED}✗ Failed to start${NC}"
            echo "Check logs: journalctl -u swath-movers-dev -n 50"
        fi
        ;;

    restart-prod)
        echo -e "${RED}WARNING: This will restart production!${NC}"
        read -p "Are you sure? (y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Restarting production service...${NC}"
            sudo systemctl restart swath-movers
            sleep 2
            if systemctl is-active --quiet swath-movers.service; then
                echo -e "${GREEN}✓ Production service restarted${NC}"
                echo ""
                echo "Test at: https://seistools.space"
            else
                echo -e "${RED}✗ Failed to start${NC}"
                echo "Check logs: journalctl -u swath-movers -n 50"
            fi
        else
            echo "Cancelled."
        fi
        ;;

    logs-dev)
        echo -e "${BLUE}Development logs (Ctrl+C to exit):${NC}"
        echo ""
        journalctl -u swath-movers-dev -f
        ;;

    logs-prod)
        echo -e "${BLUE}Production logs (Ctrl+C to exit):${NC}"
        echo ""
        journalctl -u swath-movers -f
        ;;

    test)
        echo -e "${BLUE}Testing Services:${NC}"
        echo ""
        echo -n "Production (8080):   "
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q "200\|301\|302"; then
            echo -e "${GREEN}✓ OK${NC}"
        else
            echo -e "${RED}✗ FAIL${NC}"
        fi

        echo -n "Development (8081):  "
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 | grep -q "200\|301\|302"; then
            echo -e "${GREEN}✓ OK${NC}"
        else
            echo -e "${RED}✗ FAIL${NC}"
        fi

        echo -n "Cloudflare:          "
        if curl -s -o /dev/null -w "%{http_code}" https://seistools.space | grep -q "200\|301\|302"; then
            echo -e "${GREEN}✓ OK${NC}"
        else
            echo -e "${RED}✗ FAIL${NC}"
        fi
        echo ""
        ;;

    start-dev)
        echo -e "${YELLOW}Starting development service...${NC}"
        sudo systemctl start swath-movers-dev
        sleep 2
        systemctl is-active --quiet swath-movers-dev.service && echo -e "${GREEN}✓ Started${NC}" || echo -e "${RED}✗ Failed${NC}"
        ;;

    stop-dev)
        echo -e "${YELLOW}Stopping development service...${NC}"
        sudo systemctl stop swath-movers-dev
        sleep 1
        echo -e "${GREEN}✓ Stopped${NC}"
        ;;

    new-feature)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Feature name required${NC}"
            echo "Usage: bash scripts/dev-helper.sh new-feature <feature-name>"
            echo "Example: bash scripts/dev-helper.sh new-feature polygon-selection"
            exit 1
        fi

        FEATURE_NAME=$2
        BRANCH_NAME="feature/$FEATURE_NAME"

        echo -e "${YELLOW}Creating feature branch: ${BRANCH_NAME}${NC}"
        git checkout -b "$BRANCH_NAME"
        echo -e "${GREEN}✓ Branch created and checked out${NC}"
        echo ""
        echo "Current branch: $(git branch --show-current)"
        echo ""
        echo "Next steps:"
        echo "  1. Make your changes"
        echo "  2. Restart dev: bash scripts/dev-helper.sh restart-dev"
        echo "  3. Test at: http://localhost:8081"
        echo "  4. When ready: git add . && git commit -m 'Your message'"
        echo ""
        ;;

    list-branches)
        echo -e "${BLUE}Git Branches:${NC}"
        echo ""
        git branch -a
        echo ""
        echo "Current: $(git branch --show-current)"
        echo ""
        ;;

    current-branch)
        echo ""
        echo "Current branch: $(git branch --show-current)"
        echo ""
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_usage
        exit 1
        ;;
esac
