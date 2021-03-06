"""
Modified from https://github.com/strutive07/transformer-tensorflow2.0

@author: tim

Modified https://github.com/strutive07/transformer-tensorflow2.0 model.py to create a classifying 
transformer instead of seq2seq.

Also redesigned to eliminate need for embedding layer as not doing nlp.


"""


import os

import numpy as np
import tensorflow as tf

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

class TransformerEncoder(tf.keras.layers.Layer):
    """ Tim: Modified from Original seq2seq Transformer model below and turned into layer
    """
    def __init__(self,
                 encoder_count=1,
                 attention_head_count=8,
                 d_model=2560,
                 d_point_wise_ff=2048,
                 dropout_prob=0.1,
                 add_pos_enc=True,
                 regul=None,
                 activ=None):
        super(TransformerEncoder, self).__init__()

        # model hyper parameter variables
        self.encoder_count = encoder_count
        self.attention_head_count = attention_head_count
        self.d_model = d_model
        self.d_point_wise_ff = d_point_wise_ff
        self.dropout_prob = dropout_prob
        self.add_pos_enc = add_pos_enc
        self.regul = regul
        self.activ = activ
        if self.activ is None:
            self.activ = 'relu'

        if self.add_pos_enc:
            self.pos_enc = PosEncoderLayer(d_model)
        self.encoder_input_dropout = tf.keras.layers.Dropout(dropout_prob)

        self.encoder_layers = [
            EncoderLayer(
                attention_head_count,
                d_model,
                d_point_wise_ff,
                dropout_prob, regul=regul, activ=self.activ
            ) for _ in range(encoder_count)
        ]
        #self.linear = tf.keras.layers.Dense(C["num_classes"], activation='softmax')

    def call(self,
             inputs,      #[bs, seq_len, d_model=emb_dim]
             training
             ):
        if len(inputs.shape) == 4:
            inputs = tf.keras.backend.squeeze(inputs, axis=-1)  # needed to add extra dim for conv layer so remove here
            
        if self.add_pos_enc:
            inputs = self.pos_enc(inputs)
        encoder_tensor = self.encoder_input_dropout(inputs, training=training)

        for i in range(self.encoder_count):
            encoder_tensor, _ = self.encoder_layers[i](encoder_tensor, mask=None, training=training)
        return encoder_tensor    #self.linear(encoder_tensor)



class Transformer(tf.keras.Model):
    """ Tim: Original seq2seq model
    """
    def __init__(self,
                 inputs_vocab_size,
                 target_vocab_size,
                 encoder_count,
                 decoder_count,
                 attention_head_count,
                 d_model,
                 d_point_wise_ff,
                 dropout_prob):
        super(Transformer, self).__init__()

        # model hyper parameter variables
        self.encoder_count = encoder_count
        self.decoder_count = decoder_count
        self.attention_head_count = attention_head_count
        self.d_model = d_model
        self.d_point_wise_ff = d_point_wise_ff
        self.dropout_prob = dropout_prob

        self.encoder_embedding_layer = Embeddinglayer(inputs_vocab_size, d_model)
        self.encoder_embedding_dropout = tf.keras.layers.Dropout(dropout_prob)
        self.decoder_embedding_layer = Embeddinglayer(target_vocab_size, d_model)
        self.decoder_embedding_dropout = tf.keras.layers.Dropout(dropout_prob)

        self.encoder_layers = [
            EncoderLayer(
                attention_head_count,
                d_model,
                d_point_wise_ff,
                dropout_prob
            ) for _ in range(encoder_count)
        ]

        self.decoder_layers = [
            DecoderLayer(
                attention_head_count,
                d_model,
                d_point_wise_ff,
                dropout_prob
            ) for _ in range(decoder_count)
        ]

        self.linear = tf.keras.layers.Dense(target_vocab_size)

    def call(self,
             inputs,
             target,
             inputs_padding_mask,
             look_ahead_mask,
             target_padding_mask,
             training
             ):
        encoder_tensor = self.encoder_embedding_layer(inputs)
        encoder_tensor = self.encoder_embedding_dropout(encoder_tensor, training=training)

        for i in range(self.encoder_count):
            encoder_tensor, _ = self.encoder_layers[i](encoder_tensor, inputs_padding_mask, training=training)
        target = self.decoder_embedding_layer(target)
        decoder_tensor = self.decoder_embedding_dropout(target, training=training)
        for i in range(self.decoder_count):
            decoder_tensor, _, _ = self.decoder_layers[i](
                decoder_tensor,
                encoder_tensor,
                look_ahead_mask,
                target_padding_mask,
                training=training
            )
        return self.linear(decoder_tensor)


class EncoderLayer(tf.keras.layers.Layer):
    def __init__(self, attention_head_count, d_model, d_point_wise_ff, dropout_prob, regul=None, activ='relu'):
        super(EncoderLayer, self).__init__()

        # model hyper parameter variables
        self.attention_head_count = attention_head_count
        self.d_model = d_model
        self.d_point_wise_ff = d_point_wise_ff
        self.dropout_prob = dropout_prob
        self.regul = regul

        self.multi_head_attention = MultiHeadAttention(attention_head_count, d_model)
        self.dropout_1 = tf.keras.layers.Dropout(dropout_prob)
        self.layer_norm_1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)

        self.position_wise_feed_forward_layer = PositionWiseFeedForwardLayer(
            d_point_wise_ff,
            d_model, regul=regul, activ=activ
        )
        self.dropout_2 = tf.keras.layers.Dropout(dropout_prob)
        self.layer_norm_2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)

    def call(self, inputs, mask, training):   #[bs, seq_len, d_model=emb_dim]
        output, attention = self.multi_head_attention(inputs, inputs, inputs, mask)
        output = self.dropout_1(output, training=training)
        output = self.layer_norm_1(tf.add(inputs, output))  # residual network

        output = self.position_wise_feed_forward_layer(output)
        output = self.dropout_2(output, training=training)
        output = self.layer_norm_2(tf.add(inputs, output))  # residual network

        return output, attention


class DecoderLayer(tf.keras.layers.Layer):
    def __init__(self, attention_head_count, d_model, d_point_wise_ff, dropout_prob):
        super(DecoderLayer, self).__init__()

        # model hyper parameter variables
        self.attention_head_count = attention_head_count
        self.d_model = d_model
        self.d_point_wise_ff = d_point_wise_ff
        self.dropout_prob = dropout_prob

        self.masked_multi_head_attention = MultiHeadAttention(attention_head_count, d_model)
        self.dropout_1 = tf.keras.layers.Dropout(dropout_prob)
        self.layer_norm_1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)

        self.encoder_decoder_attention = MultiHeadAttention(attention_head_count, d_model)
        self.dropout_2 = tf.keras.layers.Dropout(dropout_prob)
        self.layer_norm_2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)

        self.position_wise_feed_forward_layer = PositionWiseFeedForwardLayer(
            d_point_wise_ff,
            d_model
        )
        self.dropout_3 = tf.keras.layers.Dropout(dropout_prob)
        self.layer_norm_3 = tf.keras.layers.LayerNormalization(epsilon=1e-6)

    def call(self, decoder_inputs, encoder_output, look_ahead_mask, padding_mask, training):
        output, attention_1 = self.masked_multi_head_attention(
            decoder_inputs,
            decoder_inputs,
            decoder_inputs,
            look_ahead_mask
        )
        output = self.dropout_1(output, training=training)
        query = self.layer_norm_1(tf.add(decoder_inputs, output))  # residual network
        output, attention_2 = self.encoder_decoder_attention(
            query,
            encoder_output,
            encoder_output,
            padding_mask
        )
        output = self.dropout_2(output, training=training)
        encoder_decoder_attention_output = self.layer_norm_2(tf.add(output, query))

        output = self.position_wise_feed_forward_layer(encoder_decoder_attention_output)
        output = self.dropout_3(output, training=training)
        output = self.layer_norm_3(tf.add(encoder_decoder_attention_output, output))  # residual network

        return output, attention_1, attention_2


class PositionWiseFeedForwardLayer(tf.keras.layers.Layer):
    def __init__(self, d_point_wise_ff, d_model, regul=None, activ='relu'):
        super(PositionWiseFeedForwardLayer, self).__init__()
        self.activ = activ
        self.w_1 = tf.keras.layers.Dense(d_point_wise_ff, kernel_regularizer=regul)
        self.w_2 = tf.keras.layers.Dense(d_model, kernel_regularizer=regul)
        

    def call(self, inputs):
        inputs = self.w_1(inputs)
        if self.activ == 'relu':
            inputs = tf.nn.relu(inputs)
        elif self.activ == 'selu':
            inputs = tf.nn.selu(inputs)
        elif self.activ == 'leaky_relu':
            inputs = tf.nn.leaky_relu(inputs)
        elif self.activ == 'elu':
            inputs = tf.nn.elu(inputs)
        elif self.activ == 'swish':
            inputs = tf.nn.swish(inputs)
        return self.w_2(inputs)


class MultiHeadAttention(tf.keras.layers.Layer):
    def __init__(self, attention_head_count, d_model):
        super(MultiHeadAttention, self).__init__()

        # model hyper parameter variables
        self.attention_head_count = attention_head_count
        self.d_model = d_model

        if d_model % attention_head_count != 0:
            raise ValueError(
                "d_model({}) % attention_head_count({}) is not zero.d_model must be multiple of attention_head_count.".format(
                    d_model, attention_head_count
                )
            )

        self.d_h = d_model // attention_head_count

        self.w_query = tf.keras.layers.Dense(d_model)
        self.w_key = tf.keras.layers.Dense(d_model)
        self.w_value = tf.keras.layers.Dense(d_model)

        self.scaled_dot_product = ScaledDotProductAttention(self.d_h)

        self.ff = tf.keras.layers.Dense(d_model)

    def call(self, query, key, value, mask=None):
        batch_size = tf.shape(query)[0]

        query = self.w_query(query)
        key = self.w_key(key)
        value = self.w_value(value)

        query = self.split_head(query, batch_size)
        key = self.split_head(key, batch_size)
        value = self.split_head(value, batch_size)

        output, attention = self.scaled_dot_product(query, key, value, mask)
        output = self.concat_head(output, batch_size)

        return self.ff(output), attention

    def split_head(self, tensor, batch_size):
        # inputs tensor: (batch_size, seq_len, d_model)
        return tf.transpose(
            tf.reshape(
                tensor,
                (batch_size, -1, self.attention_head_count, self.d_h)
                # tensor: (batch_size, seq_len_splited, attention_head_count, d_h)
            ),
            [0, 2, 1, 3]
            # tensor: (batch_size, attention_head_count, seq_len_splited, d_h)
        )

    def concat_head(self, tensor, batch_size):
        return tf.reshape(
            tf.transpose(tensor, [0, 2, 1, 3]),
            (batch_size, -1, self.attention_head_count * self.d_h)
        )


class ScaledDotProductAttention(tf.keras.layers.Layer):
    """ if the shape of Q,K and V is (100, 512)
        then the shape of matmul_q_and_transposed_k will be (100,100)
        as will the shape after applying softmax. 
        The shape of tf.matmul(attention_weight, value) will once again be (100,512) ie (100,100)(100,512) = (100,512)
        
    """
    def __init__(self, d_h):
        super(ScaledDotProductAttention, self).__init__()
        self.d_h = d_h

    def call(self, query, key, value, mask=None):
        matmul_q_and_transposed_k = tf.matmul(query, key, transpose_b=True)
        scale = tf.sqrt(tf.cast(self.d_h, dtype=tf.float32))
        scaled_attention_score = matmul_q_and_transposed_k / scale
        if mask is not None:
            scaled_attention_score += (mask * -1e9)

        attention_weight = tf.nn.softmax(scaled_attention_score, axis=-1)

        return tf.matmul(attention_weight, value), attention_weight


class Embeddinglayer(tf.keras.layers.Layer):
    """ Tim: Converts [bs, seq_len] = word id  to [bs, seq_len, d_model]
             (emb_dim = d_model)
    """
    def __init__(self, vocab_size, d_model):
        # model hyper parameter variables
        super(Embeddinglayer, self).__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model

        self.embedding = tf.keras.layers.Embedding(vocab_size, d_model)

    def call(self, sequences):
        max_sequence_len = sequences.shape[1]
        output = self.embedding(sequences) * tf.sqrt(tf.cast(self.d_model, dtype=tf.float32))
        output += self.positional_encoding(max_sequence_len)

        return output

    def positional_encoding(self, max_len):
        pos = np.expand_dims(np.arange(0, max_len), axis=1)
        index = np.expand_dims(np.arange(0, self.d_model), axis=0)

        pe = self.angle(pos, index)

        pe[:, 0::2] = np.sin(pe[:, 0::2])
        pe[:, 1::2] = np.cos(pe[:, 1::2])

        pe = np.expand_dims(pe, axis=0)
        return tf.cast(pe, dtype=tf.float32)

    def angle(self, pos, index):
        return pos / np.power(10000, (index - index % 2) / np.float32(self.d_model))

    
class PosEncoderLayer(tf.keras.layers.Layer):
    """ Tim: New, separate Positional Encoding Fn since we aren't using EmbeddingLayer
        Test with: mpe = tf.keras.Sequential([PosEncoderLayer(2560)])
    """
    def __init__(self, d_model):
        # model hyper parameter variables
        super(PosEncoderLayer, self).__init__()
        self.d_model = d_model


    def call(self, sequences):   # [bs, seq_len, d_model]
        max_sequence_len = sequences.shape[1]
        output = sequences * tf.sqrt(tf.cast(self.d_model, dtype=tf.float32))
        output += self.positional_encoding(max_sequence_len)

        return output            # [bs, seq_len, d_model]

    def positional_encoding(self, max_len):
        pos = np.expand_dims(np.arange(0, max_len), axis=1)
        index = np.expand_dims(np.arange(0, self.d_model), axis=0)

        pe = self.angle(pos, index)

        pe[:, 0::2] = np.sin(pe[:, 0::2])
        pe[:, 1::2] = np.cos(pe[:, 1::2])

        pe = np.expand_dims(pe, axis=0)
        return tf.cast(pe, dtype=tf.float32)

    def angle(self, pos, index):
        return pos / np.power(10000, (index - index % 2) / np.float32(self.d_model))
