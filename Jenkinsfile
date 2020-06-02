pipeline {
  agent { label 'master' }
  options {
    timeout(time: 60, unit: 'MINUTES')
  }

  stages {
    stage ('Checkout') {
      steps {
        script {
          env.REPO_NAME = env.JOB_NAME.split('/')[1]
          env.PKG_NAME  = env.REPO_NAME.substring(0, env.REPO_NAME.length() - 4)
          checkoutRecursive(env.PKG_NAME)
        }
      }
    }

    stage ('Pre-commit Checks') {
      steps {
        script {
          dir(env.PKG_NAME) {
            preCommit()
          }
        }
      }
    }

    stage ('Build') {
      steps {
        withCredentials([string(credentialsId: 'further-link-key', variable: 'key')]) {
          sh 'python3 -c "import codecs; print(codecs.getencoder(\'rot-13\')(\'$key\')[0])" > pt-further-link/data'
        }
        buildDebPkg()
      }
    }

    stage ('Test') {
      steps {
        sh """
        cd pt-further-link
        pipenv sync --dev
        FURTHER_LINK_WORK_DIR=\$(pwd) pipenv run pytest test.py
        """

        script {
          try {
            lintian(
              packageName: env.PKG_NAME,
              useChangeFile: true,
              throwError: false
            )
          } catch (e) {
            currentBuild.result = 'UNSTABLE'
          }
        }
      }
    }

    stage ('Publish') {
      steps {
        publishSirius()
      }
    }
  }
}
