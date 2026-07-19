pipeline {
    agent {
        label 'redis-test'  // 专门的测试 agent
    }

    options {
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(
            name: 'BUILD_VERSION',
            defaultValue: '',
            description: '要测试的构建版本号（如 1.0.45-abc1234），留空则测试 latest'
        )
        
        string(
            name: 'ARTIFACT_HOST',
            defaultValue: '192.168.79.134',
            description: '制品服务器地址'
        )
        
        string(
            name: 'ARTIFACT_DIR',
            defaultValue: '/home/dong2/artifacts',
            description: '制品存放目录'
        )
        
        string(
            name: 'TEST_IMAGE',
            defaultValue: 'redis-test-runner:1.0',
            description: '测试运行环境镜像'
        )
        
        choice(
            name: 'TEST_SUITE',
            choices: ['all', 'basic', 'perf', 'persistence'],
            description: '要执行的测试套件'
        )
        
        string(
            name: 'NOTIFY_EMAILS',
            defaultValue: 'devops@company.com,qa@company.com',
            description: '测试结果通知邮箱，逗号分隔'
        )
    }

    environment {
        TEST_WORKSPACE = "/tmp/redis-test-${BUILD_NUMBER}"
        REPORT_DIR = "${WORKSPACE}/test-reports"
        REDIS_PACKAGE = "redis-${params.BUILD_VERSION}.tar.gz"
    }

    stages {
        stage("Clean Workspace") {
            steps {
                cleanWs()
                sh '''
                rm -rf ${TEST_WORKSPACE}
                mkdir -p ${TEST_WORKSPACE}
                mkdir -p ${REPORT_DIR}
                '''
            }
        }


	stage("Download Artifact") {
	    steps {
		sshagent(credentials: ['dong2-ssh-key']) {
		    script {
			def version = params.BUILD_VERSION ?: sh(
			    script: "ssh -o StrictHostKeyChecking=no dong2@${params.ARTIFACT_HOST} 'readlink ${params.ARTIFACT_DIR}/latest.tar.gz' | sed 's/latest.tar.gz/redis-&/'",
			    returnStdout: true
			).trim()
			
			if (!params.BUILD_VERSION) {
			    env.TARGET_VERSION = version.replace('redis-', '').replace('.tar.gz', '')
			} else {
			    env.TARGET_VERSION = params.BUILD_VERSION
			}
			
			echo "Testing Redis version: ${env.TARGET_VERSION}"
		    }
		    
		    sh '''
		    scp -o StrictHostKeyChecking=no \
			dong2@${ARTIFACT_HOST}:${ARTIFACT_DIR}/redis-${TARGET_VERSION}.tar.gz \
			${TEST_WORKSPACE}/
		    scp -o StrictHostKeyChecking=no \
			dong2@${ARTIFACT_HOST}:${ARTIFACT_DIR}/redis-${TARGET_VERSION}.tar.gz.md5 \
			${TEST_WORKSPACE}/
		    
		    cd ${TEST_WORKSPACE}
		    md5sum -c redis-${TARGET_VERSION}.tar.gz.md5
		    '''
		}
	    }
	}


        stage("Prepare Test Environment") {
            steps {
                // 解压安装包，准备 Redis 二进制文件
                sh '''
                cd ${TEST_WORKSPACE}
                tar xzf redis-${TARGET_VERSION}.tar.gz
                
                # 准备 Redis 服务器二进制（从 package/bin 或解压后的目录找）
                mkdir -p redis-install/bin
                cp package/bin/redis-server redis-install/bin/ 2>/dev/null || \
                cp redis/src/redis-server redis-install/bin/ 2>/dev/null || \
                find . -name redis-server -type f -exec cp {} redis-install/bin/ \
                
                cp package/bin/redis-cli redis-install/bin/ 2>/dev/null || \
                cp redis/src/redis-cli redis-install/bin/ 2>/dev/null || \
                find . -name redis-cli -type f -exec cp {} redis-install/bin/ \
                
                chmod +x redis-install/bin/*
                ls -la redis-install/bin/
                '''
            }
        }

        stage("Run Tests") {
            steps {
                // 拉取测试代码
                checkout scm  // 拉取 redis-test-pipeline 本身
                
                // 运行测试容器
                sh '''
                # 构建测试镜像（如果还没构建）
                # docker build -t ${TEST_IMAGE} -f Dockerfile .
                
                # 运行测试
                docker run --rm \
                    --name redis-test-${BUILD_NUMBER} \
                    -v ${TEST_WORKSPACE}/redis-install:/usr/local/redis:ro \
                    -v ${WORKSPACE}/tests:/tests:ro \
                    -v ${REPORT_DIR}:/test-reports \
                    -e REDIS_SERVER_PATH=/usr/local/redis/bin/redis-server \
                    -e REDIS_CLI_PATH=/usr/local/redis/bin/redis-cli \
                    -e TEST_SUITE=${TEST_SUITE} \
                    -e BUILD_VERSION=${TARGET_VERSION} \
                    ${TEST_IMAGE} \
                    -v \
                    --html=/test-reports/report.html \
                    --self-contained-html \
                    --junitxml=/test-reports/junit.xml \
                    -n auto \
                    /tests/test_redis_${TEST_SUITE}.py \
                    2>/tests || true
                '''
            }
        }

        stage("Collect Results") {
            steps {
                // 收集测试报告
                junit testResults: 'test-reports/junit.xml', allowEmptyResults: true
                
                // 归档报告
                archiveArtifacts artifacts: 'test-reports/**', allowEmptyArchive: true
                
                // 生成摘要
                script {
                    def summary = sh(
                        script: '''
                        if [ -f test-reports/junit.xml ]; then
                            python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('test-reports/junit.xml')
root = tree.getroot()
total = int(root.get('tests', 0))
failures = int(root.get('failures', 0))
errors = int(root.get('errors', 0))
skipped = int(root.get('skipped', 0))
passed = total - failures - errors - skipped
print(f'{passed}/{total}')
"
                        else
                            echo "0/0"
                        fi
                        ''',
                        returnStdout: true
                    ).trim()
                    
                    env.TEST_SUMMARY = summary
                    currentBuild.description = "Redis ${env.TARGET_VERSION} | Tests: ${summary}"
                }
            }
        }
    }

    post {
        always {
            // 清理
            sh '''
            rm -rf ${TEST_WORKSPACE}
            docker rm -f redis-test-${BUILD_NUMBER} 2>/dev/null || true
            '''
            
            // 发送邮件通知（放在 always 里确保无论成败都发）
            script {
                def status = currentBuild.result ?: 'SUCCESS'
                def statusIcon = status == 'SUCCESS' ? '✅' : status == 'UNSTABLE' ? '⚠️' : '❌'
                
                emailext(
                    subject: "${statusIcon} Redis 集成测试 [${env.TARGET_VERSION}] - ${status}",
                    to: "${params.NOTIFY_EMAILS}",
                    body: """
                    <h2>Redis 集成测试报告</h2>
                    <table border="1" cellpadding="5">
                        <tr><td><b>构建版本</b></td><td>${env.TARGET_VERSION ?: 'latest'}</td></tr>
                        <tr><td><b>测试状态</b></td><td>${status}</td></tr>
                        <tr><td><b>构建链接</b></td><td><a href="${BUILD_URL}">${BUILD_URL}</a></td></tr>
                    </table>
                    """,
                    attachLog: true,
                    attachmentsPattern: 'test-reports/*.html'
                )
            }
        }
        
        success {
            script { 
                currentBuild.description = "Redis ${env.TARGET_VERSION} | ✅ 通过"
            }
        }
        
        unstable {
            script { 
                currentBuild.description = "Redis ${env.TARGET_VERSION} | ⚠️ 不稳定"
            }
        }
        
        failure {
            script { 
                currentBuild.description = "Redis ${env.TARGET_VERSION} | ❌ 失败"
            }
        }
    }

}
