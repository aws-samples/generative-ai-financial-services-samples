#!/bin/bash

# Setting some ANSI colours for readable output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Execution time capture
current_point_time() {
    date +%s
}
# Time taen variables
step01_time_taken=0
step02_time_taken=0
step03_time_taken=0

# Runs step 0 - AOSS creation
echo -e "${YELLOW}Running${RESET} ${GREEN}'01_run_aoss.py'${RESET} ${YELLOW}for permissions, buckets creation and aoss creation...${RESET}"
start_time=$(current_point_time)
python3 01_run_aoss.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}'01_run_aoss.py'${RESET} ${YELLOW}run, completed${RESET}"
else
    echo -e "${RED}'01_run_aoss.py' failed. Exiting.${RESET}"
    exit 1
fi
end_time=$(current_point_time)
step01_time_taken=$((end_time-start_time))
echo -e "${GREEN}'01_run_aoss.py'${RESET} ${YELLOW}run, completed${RESET}"

# Waiting for few seconds
echo -e "${BLUE}Waiting briefly before next step...${RESET}"
sleep 5

# Runs step 1 - Textract
echo -e "${YELLOW}Running${RESET} ${GREEN}'02_run_textract.py'${RESET} ${YELLOW}for file upload and text extraction using Textract...${RESET}"
start_time=$(current_point_time)
python3 02_run_textract.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}'02_run_textract.py'${RESET} ${YELLOW}run, completed${RESET}"
else
    echo -e "${RED}'02_run_textract.py' failed. Exiting.${RESET}"
    exit 1
fi
end_time=$(current_point_time)
step02_time_taken=$((end_time-start_time))

echo -e "${GREEN}'02_run_textract.py'${RESET} ${YELLOW}run, completed${RESET}"

# Cooling off for few seconds
echo -e "${BLUE}Cooling off from before next step...${RESET}"
sleep 10

# Runs step 0 - AOSS creation
echo -e "${YELLOW}Running${RESET} ${GREEN}'03_run_ingestion.py'${RESET} ${YELLOW}for permissions, buckets creation and aoss creation...${RESET}"
start_time=$(current_point_time)
python3 03_run_ingestion.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}'03_run_ingestion.py'${RESET} ${YELLOW}run, completed${RESET}"
else
    echo -e "${RED}'03_run_ingestion.py' failed. Exiting.${RESET}"
    exit 1
fi
end_time=$(current_point_time)
step03_time_taken=$((end_time-start_time))
echo -e "${GREEN}'03_run_ingestion.py'${RESET} ${YELLOW}run, completed${RESET}"

# Cooling off for few seconds
echo -e "${BLUE}Cooling off for ingestion to finish...${RESET}"
sleep 15

echo -e "${RED}All scripts run completed, please inspect your Buckets, AOSS, and files created.${RESET}"
echo -e "${YELLOW}Total Execution Time for all processes.${RESET}"
echo -e "${GREEN}Step 01, for file 03_run_aoss.py: $step01_time_taken seconds.${RESET}"
echo -e "${GREEN}Step 02, for file 02_run_textract.py: $step02_time_taken seconds.${RESET}"
echo -e "${GREEN}Step 03, for file 03_run_ingestion.py: $step03_time_taken seconds.${RESET}"
