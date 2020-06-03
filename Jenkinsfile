@Library("devops-jenkins-shared-library@master") _

node("master") {
  withCredentials([string(credentialsId: 'further-link-key', variable: 'key')]) {
    sh 'python3 -c "import codecs; print(codecs.getencoder(\'rot-13\')(\'$key\')[0])" > pt-further-link/data'
  }
}

buildOSPackage()
