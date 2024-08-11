import os
import numpy as np
import pandas as pd
from PIL import Image
import concurrent.futures
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import DenseNet201
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Dense, Flatten, Dropout, GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.utils import to_categorical

# Diretórios de treino e teste
train_dir = r'C:\Users\Danni\Downloads\Nova pasta\tcc\Skin cancer ISIC The International Skin Imaging Collaboration\Train'
test_dir = r'C:\Users\Danni\Downloads\Nova pasta\tcc\Skin cancer ISIC The International Skin Imaging Collaboration\Test'

# Definir o número máximo de workers para multiprocessing
max_workers = os.cpu_count()

# Criar dataframes para armazenar os caminhos das imagens e seus rótulos
train_df = pd.DataFrame(columns=['image_path', 'label'])
test_df = pd.DataFrame(columns=['image_path', 'label'])

# Preencher os dataframes com os caminhos das imagens e seus rótulos
for label, directory in enumerate(os.listdir(train_dir)):
    for filename in os.listdir(os.path.join(train_dir, directory)):
        image_path = os.path.join(train_dir, directory, filename)
        train_df = train_df._append({'image_path': image_path, 'label': label}, ignore_index=True)

for label, directory in enumerate(os.listdir(test_dir)):
    for filename in os.listdir(os.path.join(test_dir, directory)):
        image_path = os.path.join(test_dir, directory, filename)
        test_df = test_df._append({'image_path': image_path, 'label': label}, ignore_index=True)

# Concatenar os dataframes de treino e teste
df = pd.concat([train_df, test_df], ignore_index=True)

# Definir os caminhos das imagens e os rótulos
X = df['image_path'].values
y = df['label'].values

# Dividir os dados em conjuntos de treino e teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Definir o gerador de imagens para aumento de dados
datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode='nearest'
)

# Carregar e redimensionar as imagens
def load_image(image_path):
    return np.asarray(Image.open(image_path).resize((100, 75)))

# Carregar e redimensionar as imagens usando multiprocessing
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    X_train = list(executor.map(load_image, X_train))
    X_test = list(executor.map(load_image, X_test))

# Converter listas em arrays numpy
X_train = np.array(X_train)
X_test = np.array(X_test)

# Normalizar os valores dos pixels das imagens
X_train = X_train.astype('float32') / 255.0
X_test = X_test.astype('float32') / 255.0

# Converter rótulos para one-hot encoding
y_train = to_categorical(y_train)
y_test = to_categorical(y_test)

# Definir a base pré-treinada DenseNet201 sem a última camada densa
base_model = DenseNet201(include_top=False, weights='imagenet', input_shape=(75, 100, 3))

# Adicionar camadas personalizadas no topo da base
x = GlobalAveragePooling2D()(base_model.output)
x = Dropout(0.5)(x)
x = Dense(512, activation='relu')(x)
output = Dense(9, activation='softmax')(x)

# Definir o modelo
model = Model(inputs=base_model.input, outputs=output)

# Compilar o modelo
model.compile(optimizer=Adam(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])

# Ajustar o modelo aos dados de treino
model.fit(datagen.flow(X_train, y_train, batch_size=32),
          epochs=50,
          validation_data=(X_test, y_test),
          callbacks=[ReduceLROnPlateau(factor=0.5, patience=3, min_lr=0.00001)])

# Avaliar o modelo nos dados de teste
loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f'Acurácia nos dados de teste: {accuracy * 100:.2f}%')

# Salvar o modelo
model.save('skin_cancer_model.keras',overwrite=True)

# Carregar o modelo
loaded_model = load_model('skin_cancer_model.keras', compile=False)

# Lista para armazenar os caminhos das imagens de teste e suas classes verdadeiras
test_image_paths = []
true_labels = []

# Listar os arquivos no diretório de teste
for root, dirs, files in os.walk(test_dir):
    for file in files:
        if file.endswith('.jpg'):  # Filtrar apenas arquivos .jpg
            test_image_paths.append(os.path.join(root, file))
            # Extrair a classe verdadeira do diretório pai
            true_labels.append(os.path.basename(root))

# Fazer previsões com o modelo carregado
predictions = loaded_model.predict(X_test)

# Converter as previsões em classes previstas
predicted_classes = np.argmax(predictions, axis=1)

# Calcular a acurácia
accuracy = np.mean(predicted_classes == np.argmax(y_test, axis=1)) * 100

# Exibir a acurácia do modelo
print("Acurácia do modelo carregado:", accuracy, "%")
