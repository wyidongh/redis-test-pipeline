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
            defaultValue: 'wyidongh@icloud.com',
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

	/*
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
	*/


	stage("Download Artifact") {
	    steps {
		script {
		    // 使用参数传入的版本号，不再默认 latest
		    env.TARGET_VERSION = params.BUILD_VERSION
		    if (!env.TARGET_VERSION) {
			error "BUILD_VERSION parameter is required"
		    }
		    echo "Testing Redis version: ${env.TARGET_VERSION}"
		}
		
		sh '''
		cd ${TEST_WORKSPACE}
		
		curl -o redis-${TARGET_VERSION}.tar.gz \
		    "http://192.168.79.134:8081/repository/redis-releases/redis/${TARGET_VERSION}/redis-${TARGET_VERSION}.tar.gz"
		    
		curl -o redis-${TARGET_VERSION}.tar.gz.md5 \
		    "http://192.168.79.134:8081/repository/redis-releases/redis/${TARGET_VERSION}/redis-${TARGET_VERSION}.tar.gz.md5"
		
		md5sum -c redis-${TARGET_VERSION}.tar.gz.md5
		'''
	    }
	}

	stage("Prepare Test Environment") {
	    steps {
		sh '''
		cd ${TEST_WORKSPACE}
		tar xzf redis-${TARGET_VERSION}.tar.gz
		
		mkdir -p redis-install/bin
		cp package/bin/redis-server redis-install/bin/
		cp package/bin/redis-cli redis-install/bin/
		chmod +x redis-install/bin/*
		
		# 同时复制到 workspace 下的目录（host 可见）
		mkdir -p ${WORKSPACE}/redis-bin
		cp redis-install/bin/* ${WORKSPACE}/redis-bin/
		'''
	    }
	}


	stage("Run Tests") {
	    steps {
		checkout scm
		
		sh '''
		# 创建临时容器（不启动）
		CID=$(docker create \
		    -v ${WORKSPACE}/tests:/tests \
		    -v ${REPORT_DIR}:/test-reports \
		    redis_test:1.0.0 \
		    /tests \
		    -v \
		    --html=/test-reports/report.html \
		    --self-contained-html \
		    --junitxml=/test-reports/junit.xml)
		
		# 复制 Redis 二进制到容器内的 /usr/local/bin/
		# docker cp 会保留文件权限，不需要 chmod
		docker cp ${TEST_WORKSPACE}/redis-install/bin/redis-server ${CID}:/usr/local/bin/redis-server
		docker cp ${TEST_WORKSPACE}/redis-install/bin/redis-cli ${CID}:/usr/local/bin/redis-cli
		
		# 启动并执行测试（-a 附加到输出）
		docker start -a ${CID}
		
		# 获取退出码
		EXIT_CODE=$(docker inspect ${CID} --format='{{.State.ExitCode}}')
		
		# 清理容器
		docker rm ${CID}
		
		# 如果测试失败，让 Pipeline 感知
		exit ${EXIT_CODE}
		'''
	    }
	}



	stage("Collect Results") {
	    steps {
		junit testResults: 'test-reports/junit.xml', allowEmptyResults: true
		
		script {
		    // 用 shell 工具解析 XML，不依赖 python
		    def summary = sh(
			script: '''
			if [ -f test-reports/junit.xml ]; then
			    # 用 grep/sed 提取属性
			    total=$(grep -o 'tests="[0-9]*"' test-reports/junit.xml | grep -o '[0-9]*')
			    failures=$(grep -o 'failures="[0-9]*"' test-reports/junit.xml | grep -o '[0-9]*')
			    errors=$(grep -o 'errors="[0-9]*"' test-reports/junit.xml | grep -o '[0-9]*')
			    skipped=$(grep -o 'skipped="[0-9]*"' test-reports/junit.xml | grep -o '[0-9]*')
			    
			    total=${total:-0}
			    failures=${failures:-0}
			    errors=${errors:-0}
			    skipped=${skipped:-0}
			    
			    passed=$((total - failures - errors - skipped))
			    echo "${passed}/${total}"
			else
			    echo "0/0"
			fi
			''',
			returnStdout: true
		    ).trim()
		    
		    env.TEST_SUMMARY = summary
		    currentBuild.description = "Redis ${env.TARGET_VERSION} | Tests: ${summary}"
		}
		
		archiveArtifacts artifacts: 'test-reports/**', allowEmptyArchive: true
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
                
                mail(
                    to: "${params.NOTIFY_EMAILS}",
                    subject: "${statusIcon} Redis 集成测试 [${env.TARGET_VERSION}] - ${status}",
                    body: """
                    <html>
                    <body>
                    <h2>Redis 集成测试报告</h2>
                    <table border="1" cellpadding="5" style="border-collapse: collapse;">
                        <tr style="background: #f0f0f0;">
                            <td><b>构建版本</b></td>
                            <td>${env.TARGET_VERSION}</td>
                        </tr>
                        <tr>
                            <td><b>测试状态</b></td>
                            <td>${status}</td>
                        </tr>
                        <tr>
                            <td><b>测试结果</b></td>
                            <td>${env.TEST_SUMMARY}</td>
                        </tr>
                        <tr>
                            <td><b>构建链接</b></td>
                            <td><a href="${BUILD_URL}">${BUILD_URL}</a></td>
                        </tr>
                    </table>
                    </body>
                    </html>
                    """,
                    mimeType: 'text/html',
                    from: 'handong2030@gmail.com'
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
