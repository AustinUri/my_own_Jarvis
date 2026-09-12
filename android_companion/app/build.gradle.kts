plugins {
    id("com.android.application")
}

android {
    namespace = "com.jarvis.companion"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.jarvis.companion"
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "0.1-v26"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
